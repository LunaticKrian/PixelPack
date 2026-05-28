<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getOverview, getRecentItems, getWarrantyAlerts,
  type OverviewStats, type RecentItem, type WarrantyAlert,
} from '../api/stats'
import { getQuestSummary } from '../api/quests'
import type { QuestSummary, Achievement } from '../types/quest'
import { formatCurrency, formatDays } from '../utils/format'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const router = useRouter()

const loading = ref(true)
const overview = ref<OverviewStats | null>(null)
const recentItems = ref<RecentItem[]>([])
const warrantyAlerts = ref<WarrantyAlert[]>([])
const questSummary = ref<QuestSummary | null>(null)

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
    const [ov, recent, warranty, qs] = await Promise.all([
      getOverview(),
      getRecentItems(5),
      getWarrantyAlerts(30),
      getQuestSummary(),
    ])
    overview.value = ov
    recentItems.value = recent
    warrantyAlerts.value = warranty
    questSummary.value = qs
  } catch (e) {
    console.error('Dashboard load error', e)
  } finally {
    loading.value = false
  }
}

function goToItem(id: number) {
  router.push(`/items/${id}`)
}

function goToItems() {
  router.push('/items')
}

onMounted(loadAll)
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
            <div class="portrait-frame">
              <div class="portrait-inner">
                <div class="portrait-placeholder">
                  <img src="/img/portrait.png" alt="Character Portrait" class="portrait-img" />
                </div>
              </div>
              <div class="portrait-deco top-left"></div>
              <div class="portrait-deco top-right"></div>
              <div class="portrait-deco bottom-left"></div>
              <div class="portrait-deco bottom-right"></div>
            </div>
          </div>
          <!-- Right: Info + Stats + Bars -->
          <div class="char-data-col">
            <div class="char-info">
              <div class="char-name">冒险者 {{ auth.user?.username }}</div>
              <div class="char-level">Lv.{{ level }}</div>
              <div class="char-class">物品管理者</div>
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
          </div>
        </div>

        <!-- Recent Items -->
        <div class="info-section pixel-border">
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
  grid-template-columns: 3fr 2fr;
  gap: 20px;
  align-items: start;
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
  grid-template-columns: 1fr 2fr;
  gap: 24px;
  align-items: start;
}

.char-portrait-col {
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

/* ===== Side Panel (Right) ===== */
.side-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.menu-section,
.info-section {
  background: var(--pixel-card-bg);
  padding: 16px;
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
  grid-template-columns: 1fr 1fr;
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

/* ===== Responsive ===== */
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
}

@keyframes pixel-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
