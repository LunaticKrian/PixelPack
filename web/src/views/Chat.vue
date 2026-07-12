<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNotifyStore } from '../stores/notification'
import { listSessions, createSession, listMessages, deleteSession } from '../api/chat'
import { streamChatMessage } from '../utils/sse'
import type { ChatSession, ChatMessage, CreatedTask } from '../types/chat'
import { CATEGORY_ICONS, CATEGORY_LABELS, CATEGORY_COLORS, type TaskCategory } from '../types/task'

const notify = useNotifyStore()
const router = useRouter()

const sessions = ref<ChatSession[]>([])
const activeId = ref<number | null>(null)
const messages = ref<ChatMessage[]>([])
const loading = ref(false)

const input = ref('')
const sending = ref(false)
const streamText = ref('')
const toolActive = ref(false)
const turnTasks = ref<CreatedTask[]>([])

const threadEl = ref<HTMLElement | null>(null)

async function scrollDown() {
  await nextTick()
  if (threadEl.value) threadEl.value.scrollTop = threadEl.value.scrollHeight
}

async function loadSessions() {
  sessions.value = await listSessions()
}

async function selectSession(id: number) {
  if (sending.value) return
  activeId.value = id
  loading.value = true
  try {
    messages.value = await listMessages(id)
    await scrollDown()
  } catch {
    notify.error('加载对话失败')
  } finally {
    loading.value = false
  }
}

async function startNewChat() {
  if (sending.value) return
  const s = await createSession()
  sessions.value.unshift(s)
  await selectSession(s.id)
}

async function ensureSession() {
  if (sessions.value.length === 0) {
    await startNewChat()
  } else {
    await selectSession(sessions.value[0].id)
  }
}

async function onRemoveSession(id: number) {
  if (sending.value) return
  if (!window.confirm('删除该对话？')) return
  await deleteSession(id)
  sessions.value = sessions.value.filter((s) => s.id !== id)
  if (activeId.value === id) {
    if (sessions.value.length) await selectSession(sessions.value[0].id)
    else { activeId.value = null; messages.value = [] }
  }
  notify.success('已删除')
}

async function send() {
  const content = input.value.trim()
  if (!content || sending.value || !activeId.value) return

  // 本地立即渲染用户消息
  messages.value.push({
    id: Date.now(), session_id: activeId.value, role: 'user',
    content, meta: null, created_at: new Date().toISOString(),
  })
  input.value = ''
  sending.value = true
  streamText.value = ''
  toolActive.value = false
  turnTasks.value = []
  await scrollDown()

  let errored = false
  await streamChatMessage(activeId.value, content, {
    onEvent(e) {
      if (e.type === 'delta') {
        streamText.value += e.text
        scrollDown()
      } else if (e.type === 'tool') {
        toolActive.value = true
      } else if (e.type === 'task_created') {
        turnTasks.value.push(e.task)
        notify.info(`✦ 新任务：${e.task.title}`)
        scrollDown()
      } else if (e.type === 'error') {
        errored = true
        notify.error(e.message || '生成失败')
      } else if (e.type === 'end') {
        // 收尾
      }
    },
    onError(err) {
      errored = true
      notify.error(err.message || '网络错误')
    },
  })

  // 把本轮助手回复落为正式消息
  const finalText = streamText.value.trim() || (errored ? '(生成失败)' : '(无回复)')
  messages.value.push({
    id: Date.now() + 1, session_id: activeId.value!, role: 'assistant',
    content: finalText, meta: { tasks_created: turnTasks.value.length },
    created_at: new Date().toISOString(),
  })

  sending.value = false
  streamText.value = ''
  toolActive.value = false
  turnTasks.value = []
  await scrollDown()
  // 刷新会话列表（标题/预览/计数）
  loadSessions().catch(() => {})
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function catMeta(cat: string) {
  const c = (cat as TaskCategory) || 'other'
  return { icon: CATEGORY_ICONS[c] ?? '◆', label: CATEGORY_LABELS[c] ?? cat, color: CATEGORY_COLORS[c] ?? '#b48cff' }
}

onMounted(async () => {
  try {
    await loadSessions()
    await ensureSession()
  } catch {
    notify.error('初始化对话失败')
  }
})
</script>

<template>
  <div class="chat-page animate-fade-in">
    <div class="c-layout">

      <!-- ====== 会话侧栏 ====== -->
      <aside class="c-sidebar">
        <button class="new-btn" :disabled="sending" @click="startNewChat">+ 新对话</button>
        <div class="session-list">
          <div
            v-for="s in sessions"
            :key="s.id"
            class="session-item pixel-border"
            :class="{ active: s.id === activeId, disabled: sending }"
            @click="selectSession(s.id)"
          >
            <div class="si-title">{{ s.title }}</div>
            <div class="si-meta">
              <span>{{ s.message_count }} 条</span>
              <button class="si-del" title="删除" @click.stop="onRemoveSession(s.id)">✕</button>
            </div>
          </div>
          <div v-if="sessions.length === 0" class="empty-mini">暂无对话</div>
        </div>
      </aside>

      <!-- ====== 对话主区 ====== -->
      <section class="c-main pixel-border">
        <header class="c-header">
          <div class="c-title">
            <span class="core-glyph">◉</span>
            <span class="c-name">NEXA</span>
            <span class="c-sub">// 任务生成内核</span>
          </div>
          <div class="c-status">
            <button class="goto-quests" @click="router.push('/quests')">委托大厅 ▶</button>
            <span class="dot" :class="{ busy: sending }"></span>
            <span>{{ sending ? '运行中' : '在线' }}</span>
          </div>
        </header>

        <div ref="threadEl" class="c-thread">
          <!-- 欢迎语 -->
          <div v-if="messages.length === 0 && !sending" class="welcome">
            <div class="welcome-glyph">◉</div>
            <div class="welcome-text">链路已建立。描述你今天的学习或工作计划，我会拆成任务写入清单。</div>
            <div class="welcome-hint">例如：今天考研冲刺，上午复习高数第三章，下午做英语阅读 2 篇并背 50 个单词。</div>
          </div>

          <div
            v-for="m in messages"
            :key="m.id"
            class="msg"
            :class="m.role"
          >
            <div class="msg-av">{{ m.role === 'user' ? '◈' : '◉' }}</div>
            <div class="msg-col">
              <div class="msg-name">{{ m.role === 'user' ? '你' : 'NEXA' }}</div>
              <div class="msg-bubble">{{ m.content }}</div>
            </div>
          </div>

          <!-- 流式进行中的助手消息 -->
          <div v-if="sending" class="msg assistant">
            <div class="msg-av">◉</div>
            <div class="msg-col">
              <div class="msg-name">NEXA</div>
              <div v-if="toolActive && !streamText" class="tool-line"><span class="tdot"></span> 内核运行中 · 生成任务 …</div>
              <div v-if="turnTasks.length" class="summon-list">
                <div v-for="(t, i) in turnTasks" :key="i" class="summon">
                  <span class="s-plus">▸ TASK</span>
                  <span class="s-gem" :style="{ background: catMeta(t.category).color }">{{ catMeta(t.category).icon }}</span>
                  <span class="s-title">{{ t.title }}</span>
                  <span class="s-exp">+{{ t.exp_reward }}</span>
                </div>
              </div>
              <div v-if="streamText" class="msg-bubble streaming">{{ streamText }}<span class="cursor"></span></div>
            </div>
          </div>
        </div>

        <footer class="c-compose">
          <textarea
            v-model="input"
            class="c-input"
            rows="2"
            placeholder="描述你今天的学习或工作计划…  (Enter 发送 / Shift+Enter 换行)"
            :disabled="sending"
            @keydown="onKeydown"
          ></textarea>
          <button class="c-send" :disabled="sending || !input.trim()" @click="send">
            {{ sending ? '生成中…' : '发送 ▶' }}
          </button>
        </footer>
        <div class="c-foot-hint">// NEXA 会把计划拆成任务并直接写入「委托大厅」清单</div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.chat-page { min-height: 100%; }
.c-layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 16px;
  height: calc(100vh - 140px);
  min-height: 520px;
}

/* ===== Sidebar ===== */
.c-sidebar { display: flex; flex-direction: column; gap: 10px; min-height: 0; }
.new-btn {
  font-family: var(--font-pixel), 'Ark Pixel', monospace; font-size: 12px;
  padding: 9px; background: var(--pixel-info); color: #062a30;
  border: 2px solid var(--pixel-info); cursor: pointer;
  box-shadow: 2px 2px 0 var(--pixel-shadow);
}
.new-btn:hover { filter: brightness(1.08); }
.new-btn:disabled { opacity: 0.5; cursor: default; }
.session-list { display: flex; flex-direction: column; gap: 8px; overflow-y: auto; min-height: 0; }
.session-item {
  background: var(--pixel-card-bg); padding: 8px 10px; cursor: pointer;
  transition: border-color 0.12s ease;
}
.session-item:hover { border-color: var(--pixel-info); }
.session-item.active { border-color: var(--pixel-info); box-shadow: 0 0 6px rgba(115,239,247,0.25), 3px 3px 0 var(--pixel-shadow); }
.session-item.disabled { opacity: 0.6; cursor: default; }
.si-title {
  font-family: var(--font-pixel), 'Ark Pixel', monospace; font-size: 12px;
  color: var(--pixel-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.si-meta {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 4px; font-size: 10px; color: var(--pixel-text-secondary);
  font-family: 'Press Start 2P', monospace; font-size: 8px;
}
.si-del {
  background: none; border: 1px solid var(--pixel-border); color: var(--pixel-text-secondary);
  cursor: pointer; font-size: 10px; padding: 0 4px;
}
.si-del:hover { border-color: var(--pixel-accent); color: var(--pixel-accent); }
.empty-mini { font-size: 12px; color: var(--pixel-text-secondary); padding: 12px; text-align: center; }

/* ===== Main ===== */
.c-main {
  background: var(--pixel-card-bg);
  display: flex; flex-direction: column;
  min-height: 0; position: relative;
}
.c-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; border-bottom: 2px solid var(--pixel-border);
  background: var(--pixel-bg-secondary);
}
.c-title { display: flex; align-items: center; gap: 8px; }
.core-glyph { color: var(--pixel-info); font-size: 16px; text-shadow: 0 0 8px var(--pixel-info); animation: corepulse 2s ease-in-out infinite; }
@keyframes corepulse { 50% { opacity: 0.55; } }
.c-name { font-family: 'Press Start 2P', monospace; font-size: 12px; color: var(--pixel-info); letter-spacing: 2px; text-shadow: 0 0 6px rgba(115,239,247,0.4); }
.c-sub { font-family: var(--font-pixel), 'Ark Pixel', monospace; font-size: 10px; color: var(--pixel-text-secondary); }
.c-status { display: flex; align-items: center; gap: 6px; font-family: var(--font-pixel), 'Ark Pixel', monospace; font-size: 11px; color: var(--pixel-text-secondary); }
.goto-quests {
  font-family: var(--font-pixel), 'Ark Pixel', monospace; font-size: 11px;
  background: var(--pixel-bg); border: 2px solid var(--pixel-border);
  color: var(--pixel-text-secondary); cursor: pointer; padding: 4px 10px;
}
.goto-quests:hover { border-color: var(--pixel-info); color: var(--pixel-info); }
.dot { width: 8px; height: 8px; background: var(--pixel-success); box-shadow: 0 0 6px var(--pixel-success); }
.dot.busy { background: var(--pixel-info); box-shadow: 0 0 6px var(--pixel-info); animation: corepulse 0.8s steps(2) infinite; }

/* Thread */
.c-thread {
  flex: 1; overflow-y: auto; padding: 16px;
  display: flex; flex-direction: column; gap: 14px;
  background-image:
    linear-gradient(rgba(115,239,247,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(115,239,247,0.04) 1px, transparent 1px);
  background-size: 22px 22px;
}

.welcome { text-align: center; padding: 40px 20px; color: var(--pixel-text-secondary); }
.welcome-glyph { font-size: 34px; color: var(--pixel-info); text-shadow: 0 0 12px var(--pixel-info); margin-bottom: 12px; }
.welcome-text { font-family: var(--font-pixel), 'Ark Pixel', monospace; font-size: 13px; color: var(--pixel-text); margin-bottom: 8px; }
.welcome-hint { font-size: 11px; line-height: 1.5; max-width: 420px; margin: 0 auto; }

.msg { display: flex; gap: 10px; max-width: 80%; }
.msg.user { align-self: flex-end; flex-direction: row-reverse; }
.msg.assistant { align-self: flex-start; }
.msg-av {
  width: 36px; height: 36px; flex: 0 0 36px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; background: var(--pixel-bg); border: 2px solid var(--pixel-border);
}
.msg.assistant .msg-av { border-color: var(--pixel-info); color: var(--pixel-info); box-shadow: 0 0 6px rgba(115,239,247,0.3); }
.msg-col { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.msg-name { font-family: 'Press Start 2P', monospace; font-size: 8px; color: var(--pixel-text-secondary); }
.msg.user .msg-name { text-align: right; color: var(--pixel-primary); }
.msg-bubble {
  padding: 9px 12px; background: var(--pixel-bg); border: 2px solid var(--pixel-border);
  font-family: var(--font-pixel), 'Ark Pixel', monospace; font-size: 13px; line-height: 1.55;
  word-break: break-word; white-space: pre-wrap;
  color: #ffffff;
}
.msg.assistant .msg-bubble { border-left: 3px solid var(--pixel-info); }
.msg.user .msg-bubble { background: var(--pixel-primary); color: #ffffff; border-color: var(--pixel-primary); }
.msg-bubble.streaming::after { content: ''; }

.tool-line {
  display: inline-flex; align-items: center; gap: 6px; align-self: flex-start;
  font-family: 'Press Start 2P', monospace; font-size: 8px; color: var(--pixel-info);
  padding: 5px 9px; border-left: 3px solid var(--pixel-info); background: var(--pixel-bg);
}
.tdot { width: 6px; height: 6px; background: var(--pixel-info); animation: corepulse 0.7s steps(2) infinite; }

.summon-list { display: flex; flex-direction: column; gap: 6px; }
.summon {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px; background: var(--pixel-card-bg); border: 2px solid var(--pixel-info);
  box-shadow: 2px 2px 0 var(--pixel-shadow), 0 0 8px rgba(115,239,247,0.2);
  animation: slidein 0.2s steps(5);
}
@keyframes slidein { from { transform: translateX(-10px); opacity: 0; } to { transform: none; opacity: 1; } }
.s-plus { font-family: 'Press Start 2P', monospace; font-size: 8px; color: var(--pixel-info); }
.s-gem {
  width: 22px; height: 22px; flex: 0 0 22px; display: flex; align-items: center; justify-content: center;
  font-size: 13px; color: #0c1530; border: 1px solid rgba(0,0,0,0.4);
  font-family: 'Chakra Petch', system-ui, sans-serif;
}
.s-title { font-size: 12px; color: var(--pixel-text); flex: 1; min-width: 0; }
.s-exp { font-family: 'Press Start 2P', monospace; font-size: 9px; color: var(--pixel-warning); }

.cursor {
  display: inline-block; width: 8px; height: 14px; background: var(--pixel-info);
  vertical-align: -2px; margin-left: 2px; animation: corepulse 0.7s steps(2) infinite;
}

/* Compose */
.c-compose {
  display: flex; gap: 10px; padding: 12px; border-top: 2px solid var(--pixel-border);
  background: var(--pixel-bg-secondary);
}
.c-input {
  flex: 1; font-family: var(--font-pixel), 'Ark Pixel', monospace; font-size: 13px;
  background: var(--pixel-bg); border: 2px solid var(--pixel-border); color: var(--pixel-text);
  padding: 10px 12px; resize: none; outline: none; line-height: 1.5;
}
.c-input:focus { border-color: var(--pixel-info); }
.c-input:disabled { opacity: 0.6; }
.c-send {
  font-family: var(--font-pixel), 'Ark Pixel', monospace; font-size: 12px;
  padding: 0 18px; background: var(--pixel-info); color: #062a30;
  border: 2px solid var(--pixel-info); cursor: pointer; align-self: stretch;
  box-shadow: 2px 2px 0 var(--pixel-shadow);
}
.c-send:hover:not(:disabled) { filter: brightness(1.08); }
.c-send:disabled { opacity: 0.5; cursor: default; }
.c-foot-hint {
  padding: 6px 14px 10px; background: var(--pixel-bg-secondary);
  font-family: 'Press Start 2P', monospace; font-size: 7px; color: var(--pixel-text-secondary);
  border-top: 1px solid var(--pixel-border);
}

/* ===== Responsive ===== */
@media (max-width: 800px) {
  .c-layout { grid-template-columns: 1fr; height: auto; }
  .c-sidebar { order: 2; }
  .c-main { height: calc(100vh - 220px); min-height: 420px; }
}
</style>
