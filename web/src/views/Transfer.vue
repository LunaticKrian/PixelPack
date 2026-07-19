<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'

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

const CHUNK = 16 * 1024           // 16KB / 块
const BUFFER_HIGH = 1 * 1024 * 1024  // bufferedAmount 超过 1MB 时暂停发送

// ── 文件传输状态 ────────────────────────────────────────────────────
const selectedFile = ref<File | null>(null)
const sending = ref(false)
const progress = ref(0)           // 0~100
const progressLabel = ref('')

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
  ws.onopen = () => {
    // 首帧鉴权，token 不走 URL
    ws!.send(JSON.stringify({ token }))
  }
  ws.onmessage = (ev) => onSignal(JSON.parse(ev.data))
  ws.onclose = () => {
    statusMsg.value = '信令断开，请刷新重试'
  }
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
      statusMsg.value = '把邀请码给对方，等待对方加入…'
      break
    case 'offer':
      // 我是接收方
      await onIncomingOffer(m)
      break
    case 'answer':
      await pc!.setRemoteDescription(new RTCSessionDescription(m.answer))
      break
    case 'invite_not_found':
      errorMsg.value = '邀请码无效或已过期'
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
  // 局域网直连：无需 STUN。跨网需在此追加 iceServers。
  const peer = new RTCPeerConnection({ iceServers: [] })
  peer.onconnectionstatechange = () => {
    const s = peer.connectionState
    if (s === 'connected') {
      connState.value = 'connected'
      statusMsg.value = 'P2P 通道已建立'
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
    const check = () => { if (peer.iceGatheringState === 'complete') finish() }
    peer.addEventListener('icegatheringstatechange', check)
    setTimeout(finish, timeoutMs)  // 兜底：不无限等
  })
}

// ── 发起方：建 DataChannel + 出邀请码 ───────────────────────────────
async function createInvite() {
  errorMsg.value = ''
  connState.value = 'connecting'
  pc = newPeer()
  dc = pc.createDataChannel('file', { ordered: true })
  setupDataChannel(dc)
  const offer = await pc.createOffer()
  await pc.setLocalDescription(offer)
  await waitIceComplete(pc)  // 把候选裹进 localDescription
  sendSignal({ type: 'invite_create', offer: pc.localDescription })
  statusMsg.value = '正在生成邀请码…'
}

// ── 接收方：凭码加入 ────────────────────────────────────────────────
function joinInvite() {
  errorMsg.value = ''
  if (!inputCode.value.trim()) return
  connState.value = 'connecting'
  sendSignal({ type: 'invite_join', code: inputCode.value.trim().toUpperCase() })
  statusMsg.value = '正在校验邀请码…'
}

// ── 接收方：收到 offer，建 answer ───────────────────────────────────
async function onIncomingOffer(m: any) {
  pc = newPeer()
  pc.ondatachannel = (ev) => {
    dc = ev.channel
    setupDataChannel(dc)
  }
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
    statusMsg.value = '通道就绪，可以发送文件'
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
  channel.onclose = () => {
    if (connState.value === 'connected') statusMsg.value = '通道已关闭'
  }
}

function onFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  selectedFile.value = f ?? null
  progress.value = 0
  progressLabel.value = ''
}

async function waitDrain(channel: RTCDataChannel) {
  // 发送方背压：缓冲堆积过高时等 drain，避免丢包
  if (channel.bufferedAmount < BUFFER_HIGH) return
  await new Promise<void>((resolve) => {
    const timer = setInterval(() => {
      if (channel.bufferedAmount < BUFFER_HIGH / 2) {
        clearInterval(timer)
        resolve()
      }
    }, 20)
  })
}

async function sendFile() {
  if (!dc || dc.readyState !== 'open') {
    errorMsg.value = '通道未建立'
    return
  }
  const file = selectedFile.value
  if (!file) {
    errorMsg.value = '请先选择文件'
    return
  }
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

function hangUp() {
  dc?.close()
  pc?.close()
  dc = null
  pc = null
  myCode.value = ''
  inputCode.value = ''
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
  <div class="transfer-page">
    <h1 class="title">⊳ 点对点传输</h1>
    <p class="subtitle">{{ statusMsg }}</p>
    <p v-if="errorMsg" class="error">⚠ {{ errorMsg }}</p>

    <div class="grid">
      <!-- 左：发起 / 加入 -->
      <section class="panel">
        <h2 class="panel-title">建立连接</h2>

        <div class="block">
          <button class="btn primary" :disabled="connState === 'connecting'" @click="createInvite">
            发起传输（生成邀请码）
          </button>
          <div v-if="myCode" class="code-box">
            <span class="code-label">邀请码</span>
            <span class="code">{{ myCode }}</span>
            <span class="code-hint">把码告诉对方</span>
          </div>
        </div>

        <div class="divider">— 或 —</div>

        <div class="block">
          <input
            v-model="inputCode"
            class="code-input"
            placeholder="输入对方的邀请码"
            maxlength="6"
            :disabled="connState === 'connecting'"
          />
          <button class="btn" :disabled="!inputCode || connState === 'connecting'" @click="joinInvite">
            加入
          </button>
        </div>
      </section>

      <!-- 右：文件传输 -->
      <section class="panel">
        <h2 class="panel-title">文件</h2>
        <div class="block">
          <input type="file" @change="onFileChange" :disabled="connState !== 'connected'" />
        </div>
        <div v-if="progressLabel || progress > 0" class="progress-wrap">
          <div class="progress-bar"><div class="progress-fill" :style="{ width: progress + '%' }"></div></div>
          <span class="progress-text">{{ progress }}%</span>
        </div>
        <p v-if="progressLabel" class="progress-label">{{ progressLabel }}</p>
        <div class="block">
          <button class="btn primary" :disabled="!canSend" @click="sendFile">发送</button>
          <button class="btn danger" :disabled="connState === 'idle'" @click="hangUp">断开</button>
        </div>
      </section>
    </div>

    <!-- 在线用户 -->
    <section class="panel online">
      <h2 class="panel-title">在线用户（{{ onlineUsers.length }}）</h2>
      <ul v-if="onlineUsers.length" class="user-list">
        <li v-for="u in onlineUsers" :key="u.id">
          <span class="dot"></span>{{ u.username }}
        </li>
      </ul>
      <p v-else class="empty">暂无其他在线用户</p>
    </section>
  </div>
</template>

<style scoped>
.transfer-page {
  max-width: 900px;
  margin: 0 auto;
  color: var(--pixel-text);
}
.title {
  font-family: 'Press Start 2P', monospace;
  font-size: 16px;
  color: var(--pixel-primary);
  text-shadow: 0 0 8px var(--pixel-primary);
  margin-bottom: 6px;
}
.subtitle {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 13px;
  color: var(--pixel-text-secondary);
  margin-bottom: 16px;
}
.error {
  color: var(--pixel-accent);
  font-size: 13px;
  margin-bottom: 12px;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
.panel {
  background: var(--pixel-bg-secondary);
  border: 2px solid var(--pixel-border);
  padding: 16px;
}
.panel-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  color: var(--pixel-text);
  margin-bottom: 14px;
  border-bottom: 2px solid var(--pixel-border);
  padding-bottom: 8px;
}
.block {
  margin-bottom: 14px;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.divider {
  text-align: center;
  color: var(--pixel-text-secondary);
  font-size: 12px;
  margin: 10px 0;
}
.btn {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  padding: 6px 14px;
  background: var(--pixel-bg);
  color: var(--pixel-text);
  border: 2px solid var(--pixel-border);
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease;
}
.btn:hover:not(:disabled) {
  background: var(--pixel-border);
}
.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.btn.primary {
  border-color: var(--pixel-primary);
  color: var(--pixel-primary);
}
.btn.primary:hover:not(:disabled) {
  background: var(--pixel-primary);
  color: var(--pixel-bg);
}
.btn.danger {
  border-color: var(--pixel-accent);
  color: var(--pixel-accent);
}
.btn.danger:hover:not(:disabled) {
  background: var(--pixel-accent);
  color: var(--pixel-bg);
}
.code-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 6px;
}
.code-label {
  font-size: 11px;
  color: var(--pixel-text-secondary);
}
.code {
  font-family: 'Press Start 2P', monospace;
  font-size: 22px;
  letter-spacing: 6px;
  color: var(--pixel-warning);
  text-shadow: 0 0 8px var(--pixel-warning);
}
.code-hint {
  font-size: 11px;
  color: var(--pixel-text-secondary);
}
.code-input {
  font-family: 'Press Start 2P', monospace;
  font-size: 16px;
  letter-spacing: 4px;
  text-transform: uppercase;
  background: var(--pixel-bg);
  color: var(--pixel-text);
  border: 2px solid var(--pixel-border);
  padding: 8px;
  width: 160px;
}
.code-input:focus {
  outline: none;
  border-color: var(--pixel-primary);
}
.progress-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.progress-bar {
  flex: 1;
  height: 12px;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--pixel-success);
  transition: width 0.15s ease;
}
.progress-text {
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  color: var(--pixel-text-secondary);
}
.progress-label {
  font-size: 12px;
  color: var(--pixel-text-secondary);
  margin-bottom: 12px;
}
.online .user-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
}
.online .user-list li {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 13px;
  color: var(--pixel-text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
}
.dot {
  width: 8px;
  height: 8px;
  background: var(--pixel-success);
  box-shadow: 0 0 6px var(--pixel-success);
}
.empty {
  font-size: 13px;
  color: var(--pixel-text-secondary);
}
@media (max-width: 768px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
