<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getOverview, getRecentItems, getWarrantyAlerts,
  type OverviewStats, type RecentItem, type WarrantyAlert,
} from '../api/stats'
import { getItem } from '../api/items'
import type { Item } from '../types/item'
import { getQuestSummary } from '../api/quests'
import type { QuestSummary, Achievement } from '../types/quest'
import { listJournals, createJournal, deleteJournal } from '../api/journals'
import type { Journal } from '../types/journal'
import { formatCurrency, formatDays } from '../utils/format'
import { useAuthStore } from '../stores/auth'
import CharacterInfoModal from '../components/CharacterInfoModal.vue'

const auth = useAuthStore()

const router = useRouter()

const showCharModal = ref(false)

// Item detail modal
const showDetailModal = ref(false)
const detailLoading = ref(false)
const detailItem = ref<Item | null>(null)
const detailImages = ref<{ id: number; url: string }[]>([])
const detailCosts = ref<{ id: number; name: string; amount: number }[]>([])

const statusMap: Record<string, { label: string; color: string }> = {
  ACTIVE: { label: '使用中', color: '#38b764' },
  IDLE: { label: '闲置', color: '#ef7d57' },
  RETIRED: { label: '退役', color: '#a0a0b0' },
  SOLD: { label: '已售', color: '#41a6f6' },
  DISCARDED: { label: '已弃', color: '#ff6b6b' },
}

async function openItemDetail(id: number) {
  detailLoading.value = true
  showDetailModal.value = true
  try {
    const res = await getItem(id)
    detailItem.value = res
    detailImages.value = (res as any).images || []
    detailCosts.value = (res as any).additional_costs || []
  } catch {
    showDetailModal.value = false
  } finally {
    detailLoading.value = false
  }
}

function closeDetailModal() {
  showDetailModal.value = false
  detailItem.value = null
}

const loading = ref(true)
const overview = ref<OverviewStats | null>(null)
const recentItems = ref<RecentItem[]>([])
const warrantyAlerts = ref<WarrantyAlert[]>([])
const questSummary = ref<QuestSummary | null>(null)

// Journal state
const journals = ref<Journal[]>([])
const showJournalForm = ref(false)
const journalForm = ref({ title: '', content: '', category: 'general', icon: '◈' })
const expandedJournalId = ref<number | null>(null)

const hoveredAch = ref<Achievement | null>(null)
const achTooltipStyle = ref<Record<string, string>>({})

const statusLabel: Record<string, string> = {
  ACTIVE: '使用中', IDLE: '闲置', RETIRED: '退役', SOLD: '已售', DISCARDED: '已弃',
}

// RPG stat mappings — level now includes quest EXP
const level = computed(() => questSummary.value?.level ?? (overview.value?.total_items ?? 0))
const gold = computed(() => overview.value?.total_assets_value ?? 0)
const activeCount = computed(() => overview.value?.active_items ?? 0)
const totalItems = computed(() => overview.value?.total_items ?? 1)
const hpPercent = computed(() => totalItems > 0 ? Math.round((activeCount / totalItems) * 100) : 0)
const idleCount = computed(() => totalItems - activeCount)
const mpPercent = computed(() => totalItems > 0 ? Math.min(100, Math.round((idleCount / totalItems) * 100)) : 0)
const expPercent = computed(() => {
  if (!questSummary.value) return 0
  const exp = questSummary.value.total_exp
  const currentLevel = questSummary.value.level
  const nextLevelExp = currentLevel * 50
  const prevLevelExp = (currentLevel - 1) * 50
  return Math.min(100, Math.round(((exp - prevLevelExp) / (nextLevelExp - prevLevelExp)) * 100))
})

function onAchHover(ach: Achievement, event: MouseEvent) {
  hoveredAch.value = ach
  const rect = (event.target as HTMLElement).getBoundingClientRect()
  achTooltipStyle.value = {
    position: 'fixed',
    left: rect.left + 'px',
    top: (rect.bottom + 6) + 'px',
    zIndex: '400',
  }
}

function onAchLeave() {
  hoveredAch.value = null
}

async function loadAll() {
  loading.value = true
  try {
    const [ov, recent, warranty, qs, jrnl] = await Promise.all([
      getOverview(),
      getRecentItems(5),
      getWarrantyAlerts(30),
      getQuestSummary(),
      listJournals(20),
    ])
    overview.value = ov
    recentItems.value = recent
    warrantyAlerts.value = warranty
    questSummary.value = qs
    journals.value = jrnl
  } catch (e) {
    console.error('Dashboard load error', e)
  } finally {
    loading.value = false
  }
}

function goToItem(id: number) {
  openItemDetail(id)
}

function goToItems() {
  router.push('/items')
}

// ── Journal helpers ──────────────────────────────────────────────────
async function submitJournal() {
  if (!journalForm.value.title.trim()) return
  try {
    const entry = await createJournal(journalForm.value)
    journals.value.unshift(entry)
    showJournalForm.value = false
    journalForm.value = { title: '', content: '', category: 'general', icon: '◈' }
  } catch (e) {
    console.error('Create journal error', e)
  }
}

async function removeJournal(id: number) {
  try {
    await deleteJournal(id)
    journals.value = journals.value.filter(j => j.id !== id)
  } catch (e) {
    console.error('Delete journal error', e)
  }
}

function toggleJournalExpand(id: number) {
  expandedJournalId.value = expandedJournalId.value === id ? null : id
}

function formatJournalTime(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}小时前`
  const diffDay = Math.floor(diffHr / 24)
  if (diffDay < 7) return `${diffDay}天前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function categoryLabel(cat: string): string {
  const map: Record<string, string> = {
    item_event: '物品', quest_event: '任务', achievement_event: '成就',
    general: '日常', custom: '自定义',
  }
  return map[cat] || cat
}

// ── Speech Bubble ──────────────────────────────────────────────────────
const GREETINGS = [
  '欢迎回来，冒险者！',
  '今天也要加油哦~',
  '物品整理得好，心情好！',
  '别忘了查看每日任务！',
  '有新物品要记录吗？',
  '你的背包越来越充实了！',
  '注意保修到期的物品~',
  '继续收集物品吧！',
  '冒险者，辛苦了！',
  '整理是一种超能力！',
  '每日任务完成了吗？',
  '保持良好的记录习惯！',
]

const currentGreeting = ref('')
const showBubble = ref(false)
const isTyping = ref(false)
let greetingTimer: ReturnType<typeof setTimeout> | null = null
let greetPool = [...GREETINGS].sort(() => Math.random() - 0.5)
let greetIdx = 0

function getTimeGreeting(): string {
  const h = new Date().getHours()
  if (h < 6) return '夜深了，注意休息...'
  if (h < 9) return '早上好！新的一天开始了！'
  if (h < 12) return '上午好，继续加油！'
  if (h < 14) return '午安，记得休息一下~'
  if (h < 18) return '下午好，冲冲冲！'
  if (h < 22) return '晚上好，冒险者！'
  return '夜深了，早点休息吧...'
}

function typewrite(text: string, cb?: () => void) {
  isTyping.value = true
  currentGreeting.value = ''
  let i = 0
  const tick = () => {
    if (i < text.length) {
      currentGreeting.value += text[i++]
      greetingTimer = setTimeout(tick, 50 + Math.random() * 40)
    } else {
      isTyping.value = false
      cb?.()
    }
  }
  tick()
}

function nextGreeting() {
  if (greetIdx === 0) {
    showBubble.value = true
    typewrite(getTimeGreeting(), () => {
      greetIdx++
      greetingTimer = setTimeout(nextGreeting, 7000 + Math.random() * 3000)
    })
    return
  }
  if (greetIdx >= greetPool.length) {
    greetPool = [...GREETINGS].sort(() => Math.random() - 0.5)
    greetIdx = 0
  }
  showBubble.value = false
  greetingTimer = setTimeout(() => {
    showBubble.value = true
    typewrite(greetPool[greetIdx++], () => {
      greetingTimer = setTimeout(nextGreeting, 6000 + Math.random() * 4000)
    })
  }, 350)
}

onMounted(() => {
  loadAll()
  nextGreeting()
})

onUnmounted(() => {
  if (greetingTimer) clearTimeout(greetingTimer)
})
</script>

<template>
  <div class="dashboard-page animate-fade-in">
    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="pixel-loading"></div>
      <span class="loading-text">加载中...</span>
    </div>

    <div v-else class="main-layout">
      <!-- ====== LEFT: Character Panel ====== -->
      <div class="char-panel pixel-border">
        <!-- Top: Left (Portrait) + Right (Info/Stats/Bars) -->
        <div class="char-top-row">
          <!-- Left: Portrait -->
          <div class="char-portrait-col">
            <div class="portrait-frame" @dblclick="showCharModal = true">
              <div class="portrait-inner">
                <div class="portrait-placeholder">
                  <img :src="auth.user?.portrait_url || '/img/portrait.png'" alt="Character Portrait" class="portrait-img" />
                </div>
              </div>
              <div class="portrait-deco top-left"></div>
              <div class="portrait-deco top-right"></div>
              <div class="portrait-deco bottom-left"></div>
              <div class="portrait-deco bottom-right"></div>
            </div>
            <!-- Speech Bubble (outside portrait-frame to allow overflow) -->
            <div class="speech-bubble" :class="{ visible: showBubble }">
              <div class="speech-pointer"></div>
              <span class="speech-text">{{ currentGreeting }}</span><span class="speech-cursor" :style="{ visibility: isTyping ? 'visible' : 'hidden' }">▎</span>
            </div>
          </div>
          <!-- Right: Info + Stats + Bars -->
          <div class="char-data-col">
            <div class="char-info">
              <div class="char-name">冒险者 {{ auth.user?.character_name || auth.user?.username }}</div>
              <div class="char-level">Lv.{{ level }}</div>
              <div class="char-class">{{ auth.user?.character_class?.split('|')[0] || '物品管理者' }}</div>
            </div>

            <div class="char-stats">
              <div class="stat-row-inline">
                <span class="stat-icon-gold">◆</span>
                <span class="stat-label">金币</span>
                <span class="stat-value-gold">{{ formatCurrency(gold) }}</span>
              </div>
              <div class="stat-row-inline">
                <span class="stat-icon-item">◈</span>
                <span class="stat-label">物品</span>
                <span class="stat-value">{{ totalItems }}件</span>
              </div>
              <div class="stat-row-inline">
                <span class="stat-icon-cost">▶</span>
                <span class="stat-label">日均</span>
                <span class="stat-value">{{ formatCurrency(overview?.avg_daily_cost ?? 0) }}</span>
              </div>
            </div>

            <div class="stat-bars">
              <div class="bar-group">
                <div class="bar-header">
                  <span class="bar-label">HP</span>
                  <span class="bar-value">{{ activeCount }}/{{ totalItems }}</span>
                </div>
                <div class="bar-track">
                  <div class="bar-fill hp" :style="{ width: hpPercent + '%' }"></div>
                </div>
                <div class="bar-sub">活跃物品</div>
              </div>
              <div class="bar-group">
                <div class="bar-header">
                  <span class="bar-label">MP</span>
                  <span class="bar-value">{{ idleCount }}/{{ totalItems }}</span>
                </div>
                <div class="bar-track">
                  <div class="bar-fill mp" :style="{ width: mpPercent + '%' }"></div>
                </div>
                <div class="bar-sub">闲置物品</div>
              </div>
              <div class="bar-group">
                <div class="bar-header">
                  <span class="bar-label">EXP</span>
                  <span class="bar-value">{{ expPercent }}%</span>
                </div>
                <div class="bar-track">
                  <div class="bar-fill exp" :style="{ width: expPercent + '%' }"></div>
                </div>
                <div class="bar-sub">日均消费指数</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Quest System -->
        <div class="quest-section">
          <div class="section-label">
            <span class="label-icon">▣</span>
            <span>每日任务</span>
            <span class="quest-date">{{ new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' }) }}</span>
          </div>
          <div class="quest-cards">
            <div
              v-for="q in questSummary?.daily_quests ?? []"
              :key="q.id"
              class="quest-card"
              :class="{ completed: q.completed }"
            >
              <div class="qc-name">{{ q.name }}</div>
              <div class="qc-desc">{{ q.description }}</div>
              <div class="qc-bar-track">
                <div
                  class="qc-bar-fill"
                  :class="{ done: q.completed }"
                  :style="{ width: Math.min(100, Math.round((q.progress / q.target) * 100)) + '%' }"
                ></div>
              </div>
              <div class="qc-footer">
                <span class="qc-progress">{{ q.progress }}/{{ q.target }}</span>
                <span class="qc-exp" :class="{ earned: q.completed }">
                  {{ q.completed ? '✓' : '+' }}{{ q.exp_reward }} EXP
                </span>
              </div>
            </div>
          </div>

          <!-- Achievement Badges -->
          <div class="ach-section">
            <div class="ach-header">
              <span class="ach-title">成就</span>
              <span class="ach-count">{{ questSummary?.achievements_completed ?? 0 }}/{{ questSummary?.achievements_total ?? 0 }}</span>
            </div>
            <div class="ach-grid">
              <div
                v-for="ach in questSummary?.achievements ?? []"
                :key="ach.achievement_id"
                class="ach-badge"
                :class="{ unlocked: ach.unlocked, locked: !ach.unlocked }"
                @mouseenter="onAchHover(ach, $event)"
                @mouseleave="onAchLeave"
              >
                <span class="ach-icon">{{ ach.unlocked ? ach.icon : '?' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Achievement Tooltip -->
        <Teleport to="body">
          <div v-if="hoveredAch" class="ach-tooltip" :style="achTooltipStyle">
            <div class="at-name">{{ hoveredAch.name }}</div>
            <div class="at-desc">{{ hoveredAch.description }}</div>
            <div class="at-exp">+{{ hoveredAch.exp_reward }} EXP</div>
            <div v-if="hoveredAch.unlocked && hoveredAch.unlocked_at" class="at-date">
              解锁于 {{ hoveredAch.unlocked_at.slice(0, 10) }}
            </div>
            <div v-if="!hoveredAch.unlocked" class="at-locked">未解锁</div>
          </div>
        </Teleport>
      </div>

      <!-- ====== MIDDLE: Journal Column ====== -->
      <div class="journal-panel pixel-border">
        <div class="journal-header">
          <div class="journal-header-title">
            <span class="jh-icon">◈</span>
            <span>冒险日志</span>
          </div>
          <button class="journal-add-btn" @click="showJournalForm = !showJournalForm" title="新日志">+</button>
        </div>

        <div v-if="showJournalForm" class="journal-form">
          <input
            v-model="journalForm.title"
            class="journal-form-input"
            placeholder="日志标题..."
            maxlength="200"
          />
          <textarea
            v-model="journalForm.content"
            class="journal-form-textarea"
            placeholder="详细内容 (可选)..."
            rows="3"
          ></textarea>
          <div class="journal-form-actions">
            <button class="pixel-btn primary" @click="submitJournal">记录</button>
            <button class="pixel-btn" @click="showJournalForm = false">取消</button>
          </div>
        </div>

        <div class="journal-list">
          <div v-if="journals.length === 0" class="empty-hint">暂无日志</div>
          <div
            v-for="entry in journals"
            :key="entry.id"
            class="journal-entry"
            :class="[entry.type, { expanded: expandedJournalId === entry.id }]"
            @click="toggleJournalExpand(entry.id)"
          >
            <div class="je-top-row">
              <span class="je-icon" :class="entry.category">{{ entry.icon }}</span>
              <div class="je-main">
                <div class="je-title">{{ entry.title }}</div>
                <div class="je-meta">
                  <span class="je-category">{{ categoryLabel(entry.category) }}</span>
                  <span class="je-time">{{ formatJournalTime(entry.created_at) }}</span>
                </div>
              </div>
              <button
                v-if="entry.type === 'manual'"
                class="je-delete"
                @click.stop="removeJournal(entry.id)"
                title="删除"
              >✕</button>
            </div>
            <div v-if="entry.content && expandedJournalId === entry.id" class="je-content">
              {{ entry.content }}
            </div>
          </div>
        </div>
      </div>

      <!-- ====== RIGHT: System Menu + Info ====== -->
      <div class="side-panel">
        <!-- System Menu -->
        <div class="menu-section pixel-border">
          <div class="section-header">
            <span class="section-icon">▤</span>
            <span>系统菜单</span>
          </div>
          <div class="menu-grid">
            <button class="menu-btn" @click="goToItems">
              <span class="menu-icon">◆</span>
              <span class="menu-label">背包</span>
              <span class="menu-sub">物品管理</span>
            </button>
            <button class="menu-btn" @click="router.push('/quests')">
              <span class="menu-icon">▣</span>
              <span class="menu-label">任务</span>
              <span class="menu-sub">每日任务</span>
            </button>
            <button class="menu-btn" @click="router.push('/blog')">
              <span class="menu-icon">✦</span>
              <span class="menu-label">日志</span>
              <span class="menu-sub">旅行日志</span>
            </button>
          </div>
        </div>

        <!-- Recent Items -->
        <div class="info-section recent-section pixel-border">
          <div class="section-header">
            <span class="section-icon">★</span>
            <span>最近获取</span>
          </div>
          <div v-if="recentItems.length === 0" class="empty-hint">暂无物品</div>
          <div v-else class="recent-list">
            <div
              v-for="item in recentItems"
              :key="item.id"
              class="recent-item"
              @click="goToItem(item.id)"
            >
              <div class="recent-left">
                <span class="recent-name">{{ item.name }}</span>
                <span class="recent-status" :class="item.status.toLowerCase()">
                  {{ statusLabel[item.status] || item.status }}
                </span>
              </div>
              <span class="recent-cost">{{ formatCurrency(item.daily_cost) }}/天</span>
            </div>
          </div>
        </div>

        <!-- Warranty Alerts -->
        <div class="info-section pixel-border">
          <div class="section-header">
            <span class="section-icon alert">!</span>
            <span>保修提醒</span>
          </div>
          <div v-if="warrantyAlerts.length === 0" class="empty-hint">暂无提醒</div>
          <div v-else class="alert-list">
            <div
              v-for="alert in warrantyAlerts.slice(0, 5)"
              :key="alert.id"
              class="alert-item"
              :class="{ urgent: alert.days_remaining <= 7 }"
              @click="goToItem(alert.id)"
            >
              <span class="alert-name">{{ alert.name }}</span>
              <span class="alert-days">{{ alert.days_remaining }}天</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <CharacterInfoModal :visible="showCharModal" @close="showCharModal = false" />

    <!-- Item Detail Modal -->
    <Teleport to="body">
      <div v-if="showDetailModal" class="modal-overlay" @click.self="closeDetailModal">
        <div class="modal-card">
          <div v-if="detailLoading" class="modal-loading">
            <div class="pixel-loading"></div>
          </div>
          <template v-else-if="detailItem">
            <div class="modal-header">
              <div class="modal-title-row">
                <h2 class="modal-item-name">{{ detailItem.name }}</h2>
                <span
                  class="modal-status"
                  :style="{
                    color: statusMap[detailItem.status]?.color,
                    borderColor: statusMap[detailItem.status]?.color,
                    background: (statusMap[detailItem.status]?.color || '') + '18'
                  }"
                >
                  {{ statusMap[detailItem.status]?.label || detailItem.status }}
                </span>
              </div>
              <button class="modal-close" @click="closeDetailModal">✕</button>
            </div>
            <div class="modal-body">
              <div class="modal-columns">
                <div class="modal-left">
                  <div class="modal-image-area">
                    <img
                      v-if="detailImages.length > 0"
                      :src="detailImages[0].url"
                      :alt="detailItem.name"
                      class="modal-image"
                    />
                    <div v-else class="modal-image-placeholder"><span>◆</span></div>
                  </div>
                </div>
                <div class="modal-right">
                  <div class="modal-stat-hero">
                    <div class="stat-hero-label">日均成本</div>
                    <div class="stat-hero-value">{{ formatCurrency(detailItem.daily_cost, detailItem.currency) }}</div>
                    <div class="stat-hero-unit">/ 天</div>
                  </div>
                  <div class="modal-detail-grid">
                    <div class="modal-detail-item">
                      <span class="detail-label">购买价格</span>
                      <span class="detail-value highlight">{{ formatCurrency(detailItem.purchase_price, detailItem.currency) }}</span>
                    </div>
                    <div class="modal-detail-item">
                      <span class="detail-label">总投入</span>
                      <span class="detail-value">{{ formatCurrency(detailItem.total_cost, detailItem.currency) }}</span>
                    </div>
                    <div class="modal-detail-item">
                      <span class="detail-label">使用天数</span>
                      <span class="detail-value">{{ formatDays(detailItem.usage_days) }}</span>
                    </div>
                    <div class="modal-detail-item" v-if="detailItem.purchase_channel">
                      <span class="detail-label">购买渠道</span>
                      <span class="detail-value">{{ detailItem.purchase_channel }}</span>
                    </div>
                    <div class="modal-detail-item" v-if="detailItem.current_value != null">
                      <span class="detail-label">当前价值</span>
                      <span class="detail-value">{{ formatCurrency(detailItem.current_value, detailItem.currency) }}</span>
                    </div>
                    <div class="modal-detail-item" v-if="detailItem.description">
                      <span class="detail-label">描述</span>
                      <span class="detail-value desc">{{ detailItem.description }}</span>
                    </div>
                  </div>
                  <div v-if="detailItem.tags && detailItem.tags.length" class="modal-tags">
                    <span
                      v-for="tag in detailItem.tags"
                      :key="tag.id"
                      class="modal-tag"
                      :style="{ borderColor: tag.color || 'var(--pixel-border)' }"
                    >{{ tag.name }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="modal-actions">
              <button class="pixel-btn primary" @click="router.push(`/items/${detailItem.id}`); closeDetailModal()">✎ 查看详情</button>
              <button class="pixel-btn" @click="closeDetailModal">关闭</button>
            </div>
          </template>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  gap: 16px;
}

.loading-text {
  font-family: 'Press Start 2P', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
}

/* ===== Main Layout: Left + Right ===== */
.main-layout {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 16px;
  align-items: stretch;
}

/* ===== Character Panel (Left) ===== */
.char-panel {
  background: var(--pixel-card-bg);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Top Row: Portrait | Data */
.char-top-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-items: start;
}

.char-portrait-col {
  position: relative;
  display: flex;
  justify-content: center;
}

.portrait-frame {
  position: relative;
  width: 100%;
  max-width: none;
  aspect-ratio: 10 / 13;
  border: 3px solid var(--pixel-primary);
  background: var(--pixel-bg);
  box-shadow: 3px 3px 0 var(--pixel-shadow), inset 0 0 0 3px var(--pixel-bg), inset 0 0 0 6px var(--pixel-border);
  cursor: pointer;
  transition: box-shadow 0.15s ease;
}

.portrait-frame:hover {
  box-shadow: 3px 3px 0 var(--pixel-shadow), inset 0 0 0 3px var(--pixel-bg), inset 0 0 0 6px var(--pixel-border), 0 0 12px rgba(65, 166, 246, 0.2);
}

.portrait-inner {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px;
}

.portrait-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--pixel-bg-secondary);
  border: 2px dashed var(--pixel-border);
}

.portrait-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  image-rendering: pixelated;
}

.portrait-deco {
  position: absolute;
  width: 12px;
  height: 12px;
  border: 2px solid var(--pixel-primary);
  background: var(--pixel-bg);
}

.portrait-deco.top-left { top: -4px; left: -4px; border-right: none; border-bottom: none; }
.portrait-deco.top-right { top: -4px; right: -4px; border-left: none; border-bottom: none; }
.portrait-deco.bottom-left { bottom: -4px; left: -4px; border-right: none; border-top: none; }
.portrait-deco.bottom-right { bottom: -4px; right: -4px; border-left: none; border-top: none; }

.char-data-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.char-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.char-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 18px;
  font-weight: 700;
  color: var(--pixel-primary);
  text-shadow: 0 0 8px rgba(65, 166, 246, 0.3);
}

.char-level {
  font-family: 'Press Start 2P', monospace;
  font-size: 12px;
  color: var(--pixel-warning);
  letter-spacing: 1px;
}

.char-class {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 13px;
  color: var(--pixel-text-secondary);
  border: 2px solid var(--pixel-border);
  padding: 3px 10px;
  background: var(--pixel-bg);
  display: inline-block;
  margin-top: 4px;
}

/* Stats Row */
.char-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--pixel-border);
}

.stat-row-inline {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stat-icon-gold { color: var(--pixel-warning); font-size: 14px; width: 18px; text-align: center; }
.stat-icon-item { color: var(--pixel-primary); font-size: 14px; width: 18px; text-align: center; }
.stat-icon-cost { color: var(--pixel-success); font-size: 14px; width: 18px; text-align: center; }

.stat-label {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-text-secondary);
  width: 36px;
}

.stat-value {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 13px;
  color: var(--pixel-text);
  font-weight: 600;
}

.stat-value-gold {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 13px;
  color: var(--pixel-warning);
  font-weight: 700;
}

/* Stat Bars */
.stat-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bar-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.bar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.bar-label {
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  letter-spacing: 1px;
}

.bar-group:nth-child(1) .bar-label { color: var(--pixel-success); }
.bar-group:nth-child(2) .bar-label { color: var(--pixel-info); }
.bar-group:nth-child(3) .bar-label { color: var(--pixel-warning); }

.bar-value {
  font-family: 'Press Start 2P', monospace;
  font-size: 7px;
  color: var(--pixel-text-secondary);
}

.bar-track {
  height: 16px;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  transition: width 0.5s ease-out;
  image-rendering: pixelated;
}

.bar-fill.hp { background: var(--pixel-success); box-shadow: 0 0 4px rgba(56, 183, 100, 0.3); }
.bar-fill.mp { background: var(--pixel-info); box-shadow: 0 0 4px rgba(115, 239, 247, 0.3); }
.bar-fill.exp { background: var(--pixel-warning); box-shadow: 0 0 4px rgba(239, 125, 87, 0.3); }

.bar-sub {
  font-size: 10px;
  color: var(--pixel-text-secondary);
  opacity: 0.6;
}

/* Quest Section */
.quest-section {
  border-top: 2px dashed var(--pixel-border);
  padding-top: 16px;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-text-secondary);
}

.label-icon {
  color: var(--pixel-primary);
}

.quest-date {
  margin-left: auto;
  font-size: 10px;
  opacity: 0.5;
}

.quest-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}

.quest-card {
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: border-color 0.12s ease;
}

.quest-card.completed {
  border-color: var(--pixel-success);
  background: rgba(56, 183, 100, 0.06);
}

.qc-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  font-weight: 700;
  color: var(--pixel-text);
}

.quest-card.completed .qc-name {
  color: var(--pixel-success);
}

.qc-desc {
  font-size: 10px;
  color: var(--pixel-text-secondary);
  line-height: 1.3;
}

.qc-bar-track {
  height: 6px;
  background: var(--pixel-bg-secondary);
  border: 1px solid var(--pixel-border);
  margin-top: 2px;
}

.qc-bar-fill {
  height: 100%;
  background: var(--pixel-primary);
  transition: width 0.4s ease-out;
}

.qc-bar-fill.done {
  background: var(--pixel-success);
  box-shadow: 0 0 4px rgba(56, 183, 100, 0.3);
}

.qc-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.qc-progress {
  font-size: 9px;
  color: var(--pixel-text-secondary);
  font-family: 'Press Start 2P', monospace;
}

.qc-exp {
  font-size: 9px;
  color: var(--pixel-warning);
  font-family: 'Press Start 2P', monospace;
}

.qc-exp.earned {
  color: var(--pixel-success);
}

/* Achievement Section */
.ach-section {
  border-top: 2px solid var(--pixel-border);
  padding-top: 12px;
}

.ach-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.ach-title {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
}

.ach-count {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  color: var(--pixel-text-secondary);
}

.ach-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ach-badge {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
  cursor: pointer;
  transition: border-color 0.1s ease, transform 0.1s ease;
  position: relative;
}

.ach-badge.unlocked {
  border-color: var(--pixel-warning);
  background: rgba(239, 125, 87, 0.1);
  box-shadow: 0 0 4px rgba(239, 125, 87, 0.2);
}

.ach-badge.locked {
  opacity: 0.35;
}

.ach-badge:hover {
  transform: scale(1.15);
  z-index: 10;
}

.ach-icon {
  font-size: 14px;
  line-height: 1;
}

/* Achievement Tooltip */
.ach-tooltip {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-warning);
  padding: 8px 10px;
  box-shadow: 4px 4px 0 var(--pixel-shadow);
  min-width: 140px;
  pointer-events: none;
  animation: tt-in 0.1s ease-out;
}

@keyframes tt-in {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.at-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  font-weight: 700;
  color: var(--pixel-warning);
  margin-bottom: 4px;
}

.at-desc {
  font-size: 11px;
  color: var(--pixel-text);
  line-height: 1.4;
  margin-bottom: 4px;
}

.at-exp {
  font-size: 10px;
  color: var(--pixel-primary);
  font-family: 'Press Start 2P', monospace;
}

.at-date {
  font-size: 9px;
  color: var(--pixel-text-secondary);
  margin-top: 4px;
  padding-top: 4px;
  border-top: 1px solid var(--pixel-border);
}

.at-locked {
  font-size: 9px;
  color: var(--pixel-border);
  margin-top: 4px;
}

/* ===== Journal Panel (Middle) ===== */
.journal-panel {
  background: var(--pixel-card-bg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.journal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 2px solid var(--pixel-border);
  margin-bottom: 10px;
}

.journal-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  color: var(--pixel-text-secondary);
  letter-spacing: 0.5px;
}

.jh-icon { color: var(--pixel-primary); font-size: 12px; }

.journal-add-btn {
  font-family: 'Press Start 2P', monospace;
  font-size: 12px;
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-primary);
  color: var(--pixel-primary);
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease;
}

.journal-add-btn:hover {
  background: var(--pixel-primary);
  color: var(--pixel-bg);
}

.journal-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  margin-bottom: 10px;
}

.journal-form-input,
.journal-form-textarea {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-text);
  background: var(--pixel-bg-secondary);
  border: 2px solid var(--pixel-border);
  padding: 8px;
  resize: none;
  width: 100%;
  outline: none;
  box-sizing: border-box;
}

.journal-form-input:focus,
.journal-form-textarea:focus {
  border-color: var(--pixel-primary);
  box-shadow: 0 0 0 1px var(--pixel-primary);
}

.journal-form-input::placeholder,
.journal-form-textarea::placeholder {
  color: var(--pixel-text-secondary);
  opacity: 0.5;
}

.journal-form-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.journal-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.journal-entry {
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  padding: 8px 10px;
  cursor: pointer;
  transition: border-color 0.1s ease;
}

.journal-entry:hover {
  border-color: var(--pixel-primary);
}

.journal-entry.system {
  border-left: 3px solid var(--pixel-info);
}

.journal-entry.manual {
  border-left: 3px solid var(--pixel-warning);
}

.journal-entry.expanded {
  border-color: var(--pixel-primary);
}

.je-top-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.je-icon {
  font-size: 14px;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
  line-height: 1;
}

.je-icon.item_event { color: var(--pixel-primary); }
.je-icon.quest_event { color: var(--pixel-success); }
.je-icon.achievement_event { color: var(--pixel-warning); }
.je-icon.general { color: var(--pixel-text-secondary); }

.je-main {
  flex: 1;
  min-width: 0;
}

.je-title {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  font-weight: 600;
  color: var(--pixel-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.journal-entry.expanded .je-title {
  white-space: normal;
}

.je-meta {
  display: flex;
  gap: 8px;
  margin-top: 3px;
}

.je-category {
  font-size: 9px;
  color: var(--pixel-text-secondary);
  opacity: 0.7;
}

.je-time {
  font-family: 'Press Start 2P', monospace;
  font-size: 7px;
  color: var(--pixel-text-secondary);
  opacity: 0.5;
}

.je-delete {
  background: none;
  border: none;
  color: var(--pixel-text-secondary);
  cursor: pointer;
  font-size: 11px;
  padding: 0 4px;
  opacity: 0;
  transition: opacity 0.1s ease, color 0.1s ease;
}

.journal-entry:hover .je-delete { opacity: 1; }
.je-delete:hover { color: var(--pixel-accent); }

.je-content {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
  line-height: 1.5;
  padding-top: 6px;
  margin-top: 6px;
  border-top: 1px dashed var(--pixel-border);
  white-space: pre-wrap;
}

/* ===== Side Panel (Right) ===== */
.side-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

.menu-section,
.info-section {
  background: var(--pixel-card-bg);
  padding: 16px;
}

.info-section.recent-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.info-section.recent-section .recent-list {
  overflow: hidden;
  flex: 1;
  min-height: 0;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  color: var(--pixel-text-secondary);
  letter-spacing: 0.5px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--pixel-border);
}

.section-icon {
  color: var(--pixel-primary);
  font-size: 12px;
}

.section-icon.alert {
  color: var(--pixel-accent);
}

/* Menu Grid */
.menu-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.menu-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 8px;
  background: var(--pixel-bg);
  border: 3px solid var(--pixel-border);
  color: var(--pixel-text);
  cursor: pointer;
  transition: border-color 0.12s ease, background 0.12s ease, transform 0.08s ease;
}

.menu-btn:hover {
  border-color: var(--pixel-primary);
  background: rgba(65, 166, 246, 0.08);
}

.menu-btn:active {
  transform: translate(2px, 2px);
}

.menu-btn.primary {
  border-color: var(--pixel-primary);
  background: rgba(65, 166, 246, 0.1);
}

.menu-btn.primary:hover {
  background: rgba(65, 166, 246, 0.18);
}

.menu-icon {
  font-size: 20px;
  color: var(--pixel-primary);
}

.menu-label {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 14px;
  font-weight: 700;
  color: var(--pixel-text);
}

.menu-sub {
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

/* Recent Items */
.empty-hint {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-border);
  text-align: center;
  padding: 16px;
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.recent-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  cursor: pointer;
  transition: border-color 0.1s ease;
}

.recent-item:hover {
  border-color: var(--pixel-primary);
}

.recent-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.recent-name {
  font-size: 12px;
  color: var(--pixel-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-status {
  font-size: 10px;
  opacity: 0.7;
}

.recent-status.active { color: var(--pixel-success); }
.recent-status.idle { color: var(--pixel-warning); }
.recent-status.retired { color: var(--pixel-text-secondary); }
.recent-status.sold { color: var(--pixel-primary); }
.recent-status.discarded { color: var(--pixel-accent); }

.recent-cost {
  font-size: 11px;
  color: var(--pixel-primary);
  white-space: nowrap;
  margin-left: 8px;
}

/* Alert Items */
.alert-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.alert-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  cursor: pointer;
  transition: border-color 0.1s ease;
}

.alert-item:hover {
  border-color: var(--pixel-warning);
}

.alert-item.urgent {
  border-color: var(--pixel-accent);
}

.alert-item.urgent .alert-days {
  animation: pixel-blink 0.8s step-end infinite;
}

.alert-name {
  font-size: 12px;
  color: var(--pixel-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.alert-days {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  color: var(--pixel-warning);
  flex-shrink: 0;
  margin-left: 8px;
}

.urgent .alert-days {
  color: var(--pixel-accent);
}

/* ===== Speech Bubble ===== */
.speech-bubble {
  position: absolute;
  top: 4px;
  right: -16px;
  min-width: 140px;
  max-width: 200px;
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-primary);
  box-shadow: 3px 3px 0 var(--pixel-shadow);
  padding: 10px 12px;
  z-index: 50;
  opacity: 0;
  transform: translateY(-4px) scale(0.95);
  transition: opacity 0.25s ease, transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  pointer-events: none;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text);
  line-height: 1.6;
  will-change: transform, opacity;
}

.speech-bubble.visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.speech-pointer {
  position: absolute;
  bottom: -9px;
  left: 14px;
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 9px solid var(--pixel-primary);
}

.speech-pointer::after {
  content: '';
  position: absolute;
  left: -4px;
  top: -8px;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 6px solid var(--pixel-card-bg);
}

.speech-cursor {
  display: inline;
  color: var(--pixel-primary);
  animation: cursor-blink 0.5s step-end infinite;
  font-size: 11px;
  margin-left: 1px;
}

@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* ===== Item Detail Modal ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  animation: pixel-fade-in 0.15s ease-out;
}

.modal-card {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  box-shadow: 6px 6px 0 var(--pixel-shadow);
  width: 680px;
  max-width: 92vw;
  max-height: 90vh;
  overflow-y: auto;
  animation: pixel-scale-in 0.2s ease-out;
}

.modal-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px;
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 3px solid var(--pixel-border);
  background: var(--pixel-bg-secondary);
}

.modal-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.modal-item-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 16px;
  font-weight: 700;
  color: var(--pixel-primary);
  margin: 0;
}

.modal-status {
  font-size: 10px;
  padding: 2px 8px;
  border: 2px solid;
  white-space: nowrap;
}

.modal-close {
  background: none;
  border: 2px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  font-size: 16px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  flex-shrink: 0;
}

.modal-close:hover {
  border-color: var(--pixel-accent);
  color: var(--pixel-accent);
}

.modal-body { padding: 20px; }

.modal-columns {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 20px;
}

.modal-image-area {
  width: 100%;
  aspect-ratio: 1;
  background: var(--pixel-bg);
  border: 3px solid var(--pixel-border);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.modal-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.modal-image-placeholder {
  font-size: 48px;
  color: var(--pixel-border);
}

.modal-stat-hero {
  text-align: center;
  padding: 8px 0 12px;
}

.stat-hero-label {
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

.stat-hero-value {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 20px;
  font-weight: 700;
  color: var(--pixel-primary);
}

.stat-hero-unit {
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

.modal-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 2px solid var(--pixel-border);
}

.modal-detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.modal-detail-item:has(.desc) {
  grid-column: 1 / -1;
}

.detail-label {
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

.detail-value {
  font-size: 13px;
  color: var(--pixel-text);
}

.detail-value.highlight {
  color: var(--pixel-primary);
  font-weight: 600;
}

.detail-value.desc {
  line-height: 1.5;
  white-space: pre-wrap;
}

.modal-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.modal-tag {
  font-size: 10px;
  padding: 2px 8px;
  border: 2px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  background: var(--pixel-bg);
}

.modal-actions {
  display: flex;
  gap: 8px;
  padding: 16px 20px;
  border-top: 3px solid var(--pixel-border);
  justify-content: flex-end;
}

.pixel-btn {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  padding: 8px 16px;
  border: 3px solid var(--pixel-border);
  background: var(--pixel-bg);
  color: var(--pixel-text);
  cursor: pointer;
  box-shadow: 3px 3px 0 var(--pixel-shadow);
  transition: transform 0.08s ease, box-shadow 0.15s ease;
}

.pixel-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

.pixel-btn.primary {
  background: var(--pixel-primary);
  border-color: var(--pixel-primary);
  color: var(--pixel-bg);
}

.pixel-btn.primary:hover {
  box-shadow: 3px 3px 0 var(--pixel-shadow), 0 0 6px rgba(65, 166, 246, 0.3);
}

/* ===== Responsive ===== */
@media (max-width: 1100px) {
  .main-layout {
    grid-template-columns: 1fr 1fr;
  }
  .journal-panel {
    grid-column: 1 / -1;
    max-height: 360px;
  }
}

@media (max-width: 900px) {
  .main-layout {
    grid-template-columns: 1fr;
  }

  .char-top-row {
    grid-template-columns: 1fr;
    justify-items: center;
  }

  .char-info {
    align-items: center;
    text-align: center;
  }

  .portrait-frame {
    width: 160px;
    height: 200px;
  }

  .speech-bubble {
    display: none;
  }

  .modal-columns {
    grid-template-columns: 1fr;
  }

  .journal-panel {
    grid-column: auto;
    max-height: none;
  }
}

@keyframes pixel-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

@keyframes pixel-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes pixel-scale-in {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
</style>
