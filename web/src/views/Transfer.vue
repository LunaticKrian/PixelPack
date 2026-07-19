<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'

// ── 局部设计令牌（补齐 theme.css 未覆盖的几色，与设计稿对齐）──────────
// gold / card-2 / inset / border-2

// ── 信令 WebSocket ──────────────────────────────────────────────────
let ws: WebSocket | null = null
let pc: RTCPeerConnection | null = null
let dc: RTCDataChannel | null = null

const me = ref<{ id: number; username: string } | null>(null)
const onlineUsers = ref<{ id: number; username: string }[]>([])
const connState = ref<'idle' | 'connecting' | 'connected' | 'failed'>('idle')
const statusMsg = ref('正在连接信令服务器…')
const myCode = ref('')            // 我作为发起方拿到的邀请码
const inputCode = ref('')         // 我作为接收方填写的邀请码
const errorMsg = ref('')
const peerName = ref('???')       // 对端用户名

const CHUNK = 16 * 1024           // 16KB / 块
const BUFFER_HIGH = 1 * 1024 * 1024  // bufferedAmount 超过 1MB 时暂停发送

// ── 文件传输状态 ────────────────────────────────────────────────────
const selectedFile = ref<File | null>(null)
const sending = ref(false)
const progress = ref(0)           // 0~100
const progressLabel = ref('')
const copied = ref(false)

// ── Portal Beam 状态机：把真实状态映射成光束形态 ────────────────────
const gateState = computed<'idle' | 'waiting' | 'linked' | 'transfer'>(() => {
  if (sending.value) return 'transfer'
  if (connState.value === 'connected') return 'linked'
  if (connState.value === 'connecting') return 'waiting'
  return 'idle'
})
const channelTag = computed(() =>
  ({ idle: 'EMPTY', waiting: 'SCANNING', linked: 'LINKED', transfer: 'STREAMING' }[gateState.value]),
)
const peerDot = computed(() =>
  ({ idle: 'dot--off', waiting: 'dot--wait', linked: 'dot--ok', transfer: 'dot--ok' }[gateState.value]),
)
const peerText = computed(() =>
  ({ idle: '待连接', waiting: '等待加入…', linked: '已连接', transfer: '传输中' }[gateState.value]),
)

function wsUrl(): string {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/api/rtc/signal`
}

function connectSignal() {
  const token = localStorage.getItem('access_token')
  if (!token) {
    statusMsg.value = '未登录'
    return
  }
  ws = new WebSocket(wsUrl())
  ws.onopen = () => ws!.send(JSON.stringify({ token }))   // 首帧鉴权
  ws.onmessage = (ev) => onSignal(JSON.parse(ev.data))
  ws.onclose = () => { statusMsg.value = '信令断开，请刷新重试' }
}

async function onSignal(m: any) {
  switch (m.type) {
    case 'auth_ok':
      me.value = m.me
      statusMsg.value = '已就绪'
      break
    case 'auth_failed':
      statusMsg.value = '鉴权失败，请重新登录'
      break
    case 'presence':
      onlineUsers.value = (m.users as any[]).filter((u) => u.id !== me.value?.id)
      break
    case 'invite_created':
      myCode.value = m.code
      statusMsg.value = '把频道码告诉对方，等待加入…'
      break
    case 'offer':
      peerName.value = m.username || '对端'
      await onIncomingOffer(m)
      break
    case 'answer':
      peerName.value = m.username || '对端'
      await pc!.setRemoteDescription(new RTCSessionDescription(m.answer))
      break
    case 'invite_not_found':
      errorMsg.value = '频道码无效或已过期'
      connState.value = 'failed'
      break
    case 'peer_unavailable':
      errorMsg.value = '对方已离线'
      connState.value = 'failed'
      break
  }
}

function sendSignal(obj: any) {
  ws?.send(JSON.stringify(obj))
}

// ── WebRTC：非 trickle，ICE 收集完后把候选裹进 SDP ──────────────────
function newPeer(): RTCPeerConnection {
  const peer = new RTCPeerConnection({ iceServers: [] })  // 局域网直连
  peer.onconnectionstatechange = () => {
    const s = peer.connectionState
    if (s === 'connected') {
      connState.value = 'connected'
      statusMsg.value = '通道就绪，可以投放货物'
    } else if (s === 'failed' || s === 'disconnected' || s === 'closed') {
      if (connState.value !== 'connected') connState.value = 'failed'
      statusMsg.value = `连接状态：${s}`
    }
  }
  return peer
}

function waitIceComplete(peer: RTCPeerConnection, timeoutMs = 4000): Promise<void> {
  return new Promise((resolve) => {
    if (peer.iceGatheringState === 'complete') return resolve()
    let done = false
    const finish = () => { if (!done) { done = true; resolve() } }
    peer.addEventListener('icegatheringstatechange', () => {
      if (peer.iceGatheringState === 'complete') finish()
    })
    setTimeout(finish, timeoutMs)
  })
}

async function createInvite() {
  errorMsg.value = ''
  connState.value = 'connecting'
  pc = newPeer()
  dc = pc.createDataChannel('file', { ordered: true })
  setupDataChannel(dc)
  const offer = await pc.createOffer()
  await pc.setLocalDescription(offer)
  await waitIceComplete(pc)
  sendSignal({ type: 'invite_create', offer: pc.localDescription })
  statusMsg.value = '正在生成频道码…'
}

function joinInvite() {
  errorMsg.value = ''
  if (!inputCode.value.trim()) return
  connState.value = 'connecting'
  sendSignal({ type: 'invite_join', code: inputCode.value.trim().toUpperCase() })
  statusMsg.value = '正在校验频道码…'
}

async function onIncomingOffer(m: any) {
  pc = newPeer()
  pc.ondatachannel = (ev) => { dc = ev.channel; setupDataChannel(dc) }
  await pc.setRemoteDescription(new RTCSessionDescription(m.offer))
  const answer = await pc.createAnswer()
  await pc.setLocalDescription(answer)
  await waitIceComplete(pc)
  sendSignal({ type: 'answer', to: m.from, answer: pc.localDescription })
  statusMsg.value = '已应答，等待连接…'
}

// ── DataChannel：收发文件 ──────────────────────────────────────────
function setupDataChannel(channel: RTCDataChannel) {
  channel.binaryType = 'arraybuffer'
  let meta: { name: string; size: number; mime: string } | null = null
  const chunks: ArrayBuffer[] = []
  let received = 0

  channel.onopen = () => {
    connState.value = 'connected'
    statusMsg.value = '通道就绪，可以投放货物'
  }
  channel.onmessage = async (ev) => {
    if (typeof ev.data === 'string') {
      const msg = JSON.parse(ev.data)
      if (msg.kind === 'meta') {
        meta = msg
        chunks.length = 0
        received = 0
        progress.value = 0
        progressLabel.value = `接收：${msg.name}`
      } else if (msg.kind === 'done') {
        const blob = new Blob(chunks, { type: meta?.mime || 'application/octet-stream' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = meta?.name || 'received'
        a.click()
        URL.revokeObjectURL(url)
        progress.value = 100
        progressLabel.value = `已接收：${meta?.name}`
      }
    } else {
      chunks.push(ev.data)
      received += ev.data.byteLength
      if (meta) progress.value = Math.min(99, Math.round((received / meta.size) * 100))
    }
  }
  channel.onclose = () => { if (connState.value === 'connected') statusMsg.value = '通道已关闭' }
}

function onFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  selectedFile.value = f ?? null
  progress.value = 0
  progressLabel.value = f ? `${f.name} · 已就位` : ''
}

async function waitDrain(channel: RTCDataChannel) {
  if (channel.bufferedAmount < BUFFER_HIGH) return
  await new Promise<void>((resolve) => {
    const timer = setInterval(() => {
      if (channel.bufferedAmount < BUFFER_HIGH / 2) { clearInterval(timer); resolve() }
    }, 20)
  })
}

async function sendFile() {
  if (!dc || dc.readyState !== 'open') { errorMsg.value = '通道未建立'; return }
  const file = selectedFile.value
  if (!file) { errorMsg.value = '请先选择货物'; return }
  sending.value = true
  errorMsg.value = ''
  try {
    dc.send(JSON.stringify({ kind: 'meta', name: file.name, size: file.size, mime: file.type }))
    for (let offset = 0; offset < file.size; offset += CHUNK) {
      const buf = await file.slice(offset, offset + CHUNK).arrayBuffer()
      await waitDrain(dc)
      dc.send(buf)
      progress.value = Math.round((offset / file.size) * 100)
    }
    dc.send(JSON.stringify({ kind: 'done' }))
    progress.value = 100
    progressLabel.value = `已发送：${file.name}`
  } catch (e: any) {
    errorMsg.value = `发送失败：${e.message}`
  } finally {
    sending.value = false
  }
}

async function copyCode() {
  if (!myCode.value) return
  try {
    await navigator.clipboard.writeText(myCode.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    errorMsg.value = '复制失败，请手动选择'
  }
}

function formatSize(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}

function hangUp() {
  dc?.close()
  pc?.close()
  dc = null
  pc = null
  myCode.value = ''
  inputCode.value = ''
  peerName.value = '???'
  connState.value = 'idle'
  statusMsg.value = '已断开'
  progress.value = 0
  progressLabel.value = ''
}

const canSend = computed(() => connState.value === 'connected' && !!selectedFile.value && !sending.value)

onMounted(connectSignal)
onBeforeUnmount(hangUp)
</script>

<template>
  <div class="tp">
    <!-- 页眉 -->
    <header class="tp__head">
      <div class="eyebrow"><span class="eyebrow__dot"></span>TRANSMISSION // PEER-TO-PEER GATE</div>
      <h1 class="tp__title">传送阵</h1>
      <p class="tp__sub">在两位冒险者之间建立直连通道，文件不经过任何中转。</p>
      <p v-if="errorMsg" class="tp__error">⚠ {{ errorMsg }}</p>
    </header>

    <!-- ★ Portal Beam 英雄区 -->
    <section class="gate" :data-state="gateState" aria-label="connection state">
      <!-- 我方 -->
      <div class="pillar pillar--me">
        <div class="pillar__cap"></div>
        <div class="pillar__body"></div>
        <div class="pillar__label">
          <span class="pillar__who">YOU</span>
          <span class="pillar__name">{{ me?.username ?? '…' }}</span>
          <span class="pillar__state"><i class="dot dot--ok"></i> 在线</span>
        </div>
      </div>

      <!-- 能量束 -->
      <div class="beam-wrap">
        <div class="beam">
          <div class="beam__track"></div>
          <div class="beam__flow"></div>
          <div class="beam__sprite" aria-hidden="true">▤</div>
        </div>
        <div class="channel-tag">
          <span class="channel-tag__key">CHANNEL</span>
          <span class="channel-tag__val">{{ channelTag }}</span>
        </div>
      </div>

      <!-- 对端 -->
      <div class="pillar pillar--peer">
        <div class="pillar__cap"></div>
        <div class="pillar__body"></div>
        <div class="pillar__label">
          <span class="pillar__who">PEER</span>
          <span class="pillar__name">{{ peerName }}</span>
          <span class="pillar__state"><i class="dot" :class="peerDot"></i> {{ peerText }}</span>
        </div>
      </div>
    </section>

    <!-- 控制台 + 名册 -->
    <div class="deck">
      <!-- 控制台 -->
      <section class="panel panel--console">
        <div class="panel__head">
          <h2 class="panel__title">控制台</h2>
          <span class="panel__hint">{{ statusMsg }}</span>
        </div>

        <!-- 频道码 -->
        <div class="freq">
          <div class="freq__col">
            <span class="freq__label">发起频道</span>
            <button class="btn btn--primary" :disabled="connState === 'connecting'" @click="createInvite">
              生成频道码
            </button>
            <div v-if="myCode" class="code-slot code-slot--out">
              <span class="code-slot__caption">频道码</span>
              <span class="code">{{ myCode }}</span>
              <button class="copy" @click="copyCode">{{ copied ? '已复制' : '复制' }}</button>
            </div>
          </div>

          <div class="freq__sep">或</div>

          <div class="freq__col">
            <span class="freq__label">加入频道</span>
            <div class="join">
              <input
                v-model="inputCode"
                class="join__input"
                placeholder="输入码"
                maxlength="6"
                :disabled="connState === 'connecting'"
                @keyup.enter="joinInvite"
              />
              <button class="btn" :disabled="!inputCode || connState === 'connecting'" @click="joinInvite">加入</button>
            </div>
            <span class="freq__note">输入对方的 6 位频道码即视为同意接收</span>
          </div>
        </div>

        <hr class="pixel-divider" />

        <!-- 货物 -->
        <div class="cargo">
          <label class="dropzone" :class="{ 'is-ready': selectedFile }">
            <input type="file" @change="onFileChange" />
            <span class="dropzone__icon">▤</span>
            <span class="dropzone__text" v-if="selectedFile">
              <strong>{{ selectedFile.name }}</strong>
              <em>{{ formatSize(selectedFile.size) }} · 已就位</em>
            </span>
            <span class="dropzone__text" v-else>
              <strong>选择货物</strong>
              <em>点击选择要传送的文件</em>
            </span>
            <span class="dropzone__action">{{ selectedFile ? '更换' : '浏览' }}</span>
          </label>

          <div v-if="progress > 0 || progressLabel" class="progress">
            <div class="progress__bar"><div class="progress__fill" :style="{ width: progress + '%' }"></div></div>
            <div class="progress__meta">
              <span class="progress__pct">{{ progress }}%</span>
              <span class="progress__rate">{{ progressLabel }}</span>
            </div>
          </div>

          <div class="actions">
            <button class="btn btn--primary btn--lg" :disabled="!canSend" @click="sendFile">
              {{ sending ? '传输中…' : '投放货物' }}
            </button>
            <button class="btn btn--danger" :disabled="connState === 'idle'" @click="hangUp">切断通道</button>
          </div>
        </div>
      </section>

      <!-- 在线冒险者 -->
      <aside class="panel panel--roster">
        <div class="panel__head">
          <h2 class="panel__title">在线冒险者</h2>
          <span class="panel__count">{{ onlineUsers.length }}</span>
        </div>
        <ul v-if="onlineUsers.length" class="roster">
          <li
            v-for="u in onlineUsers"
            :key="u.id"
            class="roster__item"
            :class="{ 'roster__item--active': u.username === peerName }"
          >
            <i class="dot dot--ok"></i>
            <span class="roster__name">{{ u.username }}</span>
            <span v-if="u.username === peerName" class="roster__tag">连线中</span>
          </li>
        </ul>
        <p v-else class="roster__empty">附近没有其他冒险者。<br />邀请一位伙伴上线吧。</p>
      </aside>
    </div>
  </div>
</template>

<style scoped>
/* 局部令牌：补齐 theme.css 未覆盖的几色，与设计稿完全对齐 */
.tp {
  --gold: #f5d976;
  --card-2: #2a3f78;
  --inset: #141a36;
  --border-2: #5570b0;

  max-width: 1040px;
  margin: 0 auto;
  color: var(--pixel-text);
}
* { border-radius: 0 !important; }

/* ── 页眉 ── */
.tp__head { margin-bottom: 22px; }
.eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  font-family: var(--font-pixel-en), monospace; font-size: 8px; letter-spacing: 2px;
  color: var(--pixel-info); margin-bottom: 10px;
}
.eyebrow__dot {
  width: 7px; height: 7px; background: var(--pixel-info);
  box-shadow: 0 0 6px var(--pixel-info); animation: tp-blink 1.4s steps(2) infinite;
}
.tp__title {
  font-family: var(--font-pixel-en), monospace; font-size: 26px; letter-spacing: 2px;
  color: var(--pixel-text);
  text-shadow: 3px 3px 0 var(--pixel-shadow), 0 0 14px rgba(115, 239, 247, 0.25);
  margin: 0;
}
.tp__sub { margin-top: 8px; color: var(--pixel-text-secondary); font-size: 13px; }
.tp__error { margin-top: 10px; color: var(--pixel-accent); font-size: 13px; }

/* ── ★ Portal Beam ── */
.gate {
  display: grid; grid-template-columns: auto 1fr auto;
  align-items: center; gap: 18px;
  padding: 26px 28px;
  background: linear-gradient(180deg, var(--card-2) 0%, var(--pixel-card-bg) 100%);
  border: 3px solid var(--pixel-border);
  box-shadow: 3px 3px 0 var(--pixel-shadow), inset 0 0 0 1px rgba(115, 239, 247, 0.05);
  position: relative; overflow: hidden;
}
.gate::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, transparent, var(--pixel-info), transparent);
  opacity: 0.35;
}

.pillar { display: flex; flex-direction: column; align-items: center; gap: 8px; width: 96px; }
.pillar__cap { width: 30px; height: 10px; background: var(--border-2); box-shadow: inset -2px -2px 0 rgba(0, 0, 0, 0.3); }
.pillar__body {
  width: 18px; height: 64px; background: var(--pixel-border);
  box-shadow: inset 2px 0 0 rgba(255, 255, 255, 0.06); position: relative;
}
.pillar__body::after {
  content: ''; position: absolute; top: -6px; left: 50%; transform: translateX(-50%);
  width: 10px; height: 10px; background: var(--pixel-text-secondary);
}
.pillar__label { text-align: center; display: flex; flex-direction: column; gap: 3px; }
.pillar__who { font-family: var(--font-pixel-en), monospace; font-size: 7px; color: var(--pixel-text-secondary); letter-spacing: 1px; }
.pillar__name { font-size: 14px; font-weight: 700; }
.pillar__state { font-size: 11px; color: var(--pixel-text-secondary); display: inline-flex; align-items: center; gap: 5px; justify-content: center; }

.dot { width: 8px; height: 8px; display: inline-block; }
.dot--ok { background: var(--pixel-success); box-shadow: 0 0 6px var(--pixel-success); }
.dot--wait { background: var(--pixel-warning); box-shadow: 0 0 6px var(--pixel-warning); animation: tp-blink 1s steps(2) infinite; }
.dot--off { background: var(--pixel-text-secondary); }

/* 能量束 */
.beam-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 0 4px; }
.beam { position: relative; width: 100%; height: 64px; display: flex; align-items: center; }
.beam__track {
  position: absolute; left: 0; right: 0; top: 50%; transform: translateY(-50%); height: 6px;
  background: repeating-linear-gradient(90deg, var(--pixel-border) 0 6px, transparent 6px 12px);
  opacity: 0.6;
}
.beam__flow {
  position: absolute; left: 0; right: 0; top: 50%; transform: translateY(-50%); height: 10px;
  background: repeating-linear-gradient(90deg, var(--pixel-info) 0 8px, transparent 8px 20px);
  filter: drop-shadow(0 0 6px var(--pixel-info)); opacity: 0;
}
.beam__sprite {
  position: absolute; top: 50%; transform: translateY(-50%);
  font-size: 18px; color: var(--gold); filter: drop-shadow(0 0 6px var(--gold));
  left: 0; opacity: 0;
}

.channel-tag {
  display: inline-flex; align-items: center; gap: 8px;
  background: var(--inset); border: 3px solid var(--pixel-border);
  padding: 5px 12px; box-shadow: 3px 3px 0 var(--pixel-shadow);
}
.channel-tag__key { font-family: var(--font-pixel-en), monospace; font-size: 7px; color: var(--pixel-text-secondary); letter-spacing: 1px; }
.channel-tag__val { font-family: var(--font-pixel-en), monospace; font-size: 11px; color: var(--pixel-info); letter-spacing: 2px; }

/* 状态驱动 */
[data-state='idle'] .pillar__body::after { background: var(--pixel-text-secondary); }
[data-state='idle'] .beam__track { opacity: 0.35; }
[data-state='idle'] .channel-tag__val { color: var(--pixel-text-secondary); }

[data-state='waiting'] .pillar--me .pillar__body::after { background: var(--pixel-warning); box-shadow: 0 0 8px var(--pixel-warning); }
[data-state='waiting'] .pillar--peer .pillar__body::after { background: var(--pixel-text-secondary); }
[data-state='waiting'] .beam__flow { opacity: 0.5; animation: tp-scan 1.4s steps(14) infinite; }
[data-state='waiting'] .channel-tag__val { color: var(--pixel-warning); }

[data-state='linked'] .pillar__body::after { background: var(--pixel-success); box-shadow: 0 0 8px var(--pixel-success); }
[data-state='linked'] .beam__flow { opacity: 0.9; animation: tp-flow 1.1s linear infinite; }
[data-state='linked'] .channel-tag__val { color: var(--pixel-success); }

[data-state='transfer'] .pillar__body::after { background: var(--pixel-info); box-shadow: 0 0 10px var(--pixel-info); }
[data-state='transfer'] .beam__flow { opacity: 1; animation: tp-flow 0.7s linear infinite; }
[data-state='transfer'] .beam__sprite { opacity: 1; animation: tp-travel 2.6s linear infinite; }
[data-state='transfer'] .channel-tag__val { color: var(--pixel-info); }

@keyframes tp-flow { from { background-position: 0 0; } to { background-position: 40px 0; } }
@keyframes tp-scan { 0% { background-position: -40px 0; opacity: 0.15; } 50% { opacity: 0.7; } 100% { background-position: 40px 0; opacity: 0.15; } }
@keyframes tp-travel { from { left: 0; } to { left: calc(100% - 18px); } }
@keyframes tp-blink { 50% { opacity: 0.25; } }

/* ── 甲板 ── */
.deck { display: grid; grid-template-columns: 1fr 300px; gap: 16px; margin-top: 16px; }
.panel {
  background: var(--pixel-card-bg); border: 3px solid var(--pixel-border);
  box-shadow: 3px 3px 0 var(--pixel-shadow); padding: 16px 18px;
}
.panel__head {
  display: flex; align-items: baseline; justify-content: space-between;
  border-bottom: 2px solid var(--pixel-border); padding-bottom: 10px; margin-bottom: 14px;
}
.panel__title { font-family: var(--font-pixel-en), monospace; font-size: 10px; letter-spacing: 1px; margin: 0; }
.panel__hint { font-size: 12px; color: var(--pixel-text-secondary); }
.panel__count { font-family: var(--font-pixel-num), monospace; font-size: 20px; color: var(--pixel-success); line-height: 1; }

/* 频道码 */
.freq { display: grid; grid-template-columns: 1fr auto 1fr; align-items: start; gap: 12px; }
.freq__col { display: flex; flex-direction: column; gap: 8px; }
.freq__label { font-family: var(--font-pixel-en), monospace; font-size: 7px; color: var(--pixel-text-secondary); letter-spacing: 1px; }
.freq__sep { align-self: center; color: var(--pixel-text-secondary); font-size: 12px; padding-top: 18px; }
.freq__note { font-size: 11px; color: var(--pixel-text-secondary); }

.code-slot {
  display: flex; align-items: center; gap: 8px;
  background: var(--inset); border: 3px solid var(--pixel-border); box-shadow: 3px 3px 0 var(--pixel-shadow);
  padding: 6px 10px;
}
.code-slot--out { justify-content: space-between; }
.code-slot__caption { font-family: var(--font-pixel-en), monospace; font-size: 7px; color: var(--pixel-text-secondary); }
.code {
  font-family: var(--font-pixel-en), monospace; font-size: 20px; letter-spacing: 4px;
  color: var(--gold); text-shadow: 0 0 10px rgba(245, 217, 118, 0.5);
  flex: 1; text-align: center;
}
.copy { font-size: 11px; color: var(--pixel-info); border-bottom: 2px solid var(--pixel-info); padding: 0 2px; }

.join { display: flex; gap: 6px; }
.join__input {
  flex: 1; background: var(--inset); border: 3px solid var(--pixel-border); padding: 8px 10px;
  font-family: var(--font-pixel-en), monospace; font-size: 14px; letter-spacing: 3px; text-transform: uppercase;
  color: var(--pixel-text);
}
.join__input::placeholder { color: var(--pixel-text-secondary); letter-spacing: 2px; }
.join__input:focus { outline: 3px solid var(--pixel-info); outline-offset: -1px; border-color: var(--pixel-info); }

.pixel-divider {
  border: none; height: 3px; margin: 16px 0;
  background: repeating-linear-gradient(90deg, var(--pixel-border) 0 4px, transparent 4px 8px);
}

/* 货物 */
.cargo { display: flex; flex-direction: column; gap: 14px; }
.dropzone {
  display: flex; align-items: center; gap: 12px;
  border: 3px dashed var(--border-2); background: var(--inset);
  padding: 12px 14px; cursor: pointer; transition: border-color 0.12s steps(2);
}
.dropzone input { display: none; }
.dropzone:hover, .dropzone.is-ready { border-color: var(--pixel-info); }
.dropzone__icon { font-size: 22px; color: var(--pixel-info); }
.dropzone__text { flex: 1; display: flex; flex-direction: column; }
.dropzone__text strong { font-size: 14px; }
.dropzone__text em { font-size: 11px; color: var(--pixel-text-secondary); font-style: normal; }
.dropzone__action { font-size: 12px; color: var(--pixel-info); }

.progress { display: flex; flex-direction: column; gap: 6px; }
.progress__bar { height: 16px; background: var(--inset); border: 3px solid var(--pixel-border); overflow: hidden; position: relative; }
.progress__fill {
  height: 100%;
  background: repeating-linear-gradient(90deg, var(--pixel-success) 0 8px, #2f9a52 8px 12px);
  background-size: 12px 12px;
  animation: tp-flow 1s linear infinite;
  box-shadow: inset 0 -3px 0 rgba(0, 0, 0, 0.25);
  transition: width 0.2s steps(10);
}
.progress__meta { display: flex; justify-content: space-between; align-items: baseline; }
.progress__pct { font-family: var(--font-pixel-en), monospace; font-size: 12px; color: var(--pixel-success); }
.progress__rate { font-family: var(--font-pixel-num), monospace; font-size: 16px; color: var(--pixel-text-secondary); }

.actions { display: flex; gap: 10px; }

/* 按钮 */
.btn {
  font-weight: 700; font-size: 13px; padding: 8px 16px;
  background: var(--card-2); color: var(--pixel-text);
  border: 3px solid var(--pixel-border); box-shadow: 3px 3px 0 var(--pixel-shadow);
  transition: transform 0.08s steps(2), box-shadow 0.08s steps(2);
  cursor: pointer;
}
.btn:hover:not(:disabled) { background: var(--pixel-border); }
.btn:active:not(:disabled) { transform: translate(3px, 3px); box-shadow: none; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn--primary { background: var(--pixel-primary); border-color: var(--pixel-primary); color: var(--pixel-bg); }
.btn--primary:hover:not(:disabled) { background: var(--pixel-info); border-color: var(--pixel-info); }
.btn--danger { background: var(--pixel-accent); border-color: var(--pixel-accent); color: var(--pixel-text); }
.btn--lg { padding: 10px 22px; font-size: 14px; }

/* 名册 */
.roster { display: flex; flex-direction: column; gap: 6px; list-style: none; margin: 0; padding: 0; }
.roster__item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; background: var(--inset); border: 2px solid var(--pixel-border);
}
.roster__item--active { border-color: var(--pixel-success); box-shadow: inset 0 0 0 1px rgba(56, 183, 100, 0.3); }
.roster__name { flex: 1; font-size: 14px; }
.roster__tag { font-family: var(--font-pixel-en), monospace; font-size: 7px; letter-spacing: 1px; color: var(--pixel-success); }
.roster__empty { color: var(--pixel-text-secondary); font-size: 13px; line-height: 1.6; padding: 8px 4px; margin: 0; }

/* 响应式 */
@media (max-width: 820px) {
  .deck { grid-template-columns: 1fr; }
  .freq { grid-template-columns: 1fr; }
  .freq__sep { display: none; }
  .gate { padding: 20px 14px; gap: 10px; }
  .pillar { width: 72px; }
  .tp__title { font-size: 20px; }
}

@media (prefers-reduced-motion: reduce) {
  .beam__flow, .beam__sprite, .progress__fill, .eyebrow__dot, .dot--wait { animation: none !important; }
}
</style>
