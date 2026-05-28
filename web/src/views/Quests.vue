<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getQuestSummary } from '../api/quests'
import type { QuestSummary, Achievement, DailyQuest } from '../types/quest'
import { useAuthStore } from '../stores/auth'
import { useNotifyStore } from '../stores/notification'

const auth = useAuthStore()
const notify = useNotifyStore()
const router = useRouter()

const loading = ref(true)
const summary = ref<QuestSummary | null>(null)
const hoveredAch = ref<Achievement | null>(null)
const achTooltipStyle = ref<Record<string, string>>({})
const tab = ref<'daily' | 'achievements'>('daily')

const expandedSections = ref<Record<string, boolean>>({
  level: true,
  daily: true,
  achProgress: true,
})

function toggleSection(key: string) {
  expandedSections.value[key] = !expandedSections.value[key]
}

const completedCount = computed(() => summary.value?.daily_quests.filter(q => q.completed).length ?? 0)
const totalDailyExp = computed(() => summary.value?.daily_quests.reduce((s, q) => s + q.exp_reward, 0) ?? 0)
const earnedDailyExp = computed(() => summary.value?.daily_quests.filter(q => q.completed).reduce((s, q) => s + q.exp_reward, 0) ?? 0)
const totalAchExp = computed(() => summary.value?.achievements.reduce((s, a) => s + a.exp_reward, 0) ?? 0)
const unlockedAchExp = computed(() => summary.value?.achievements.filter(a => a.unlocked).reduce((s, a) => s + a.exp_reward, 0) ?? 0)

const expPercent = computed(() => {
  if (!summary.value) return 0
  const exp = summary.value.total_exp
  const lvl = summary.value.level
  const prev = (lvl - 1) * 50
  const next = lvl * 50
  return Math.min(100, Math.round(((exp - prev) / (next - prev)) * 100))
})

const expToNext = computed(() => {
  if (!summary.value) return 0
  return summary.value.level * 50 - summary.value.total_exp
})

const todayStr = computed(() => new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' }))

const dailyPercent = computed(() => {
  const total = summary.value?.daily_quests.length ?? 0
  return total > 0 ? Math.round((completedCount.value / total) * 100) : 0
})

const achPercent = computed(() => {
  const total = summary.value?.achievements_total ?? 0
  return total > 0 ? Math.round(((summary.value?.achievements_completed ?? 0) / total) * 100) : 0
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

async function loadSummary() {
  loading.value = true
  try {
    summary.value = await getQuestSummary()
  } catch {
    notify.error('加载任务数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadSummary)
</script>

<template>
  <div class="quests-page animate-fade-in">
    <div class="q-layout">
      <!-- ====== LEFT: Stats Sidebar ====== -->
      <div class="q-sidebar">
        <!-- Character Mini -->
        <div class="portrait-card pixel-border">
          <div class="pc-frame">
            <img src="/img/portrait.png" alt="Character" class="pc-img" />
          </div>
          <div class="pc-info">
            <div class="pc-name">冒险者 {{ auth.user?.username }}</div>
            <div class="pc-level">Lv.{{ summary?.level ?? 0 }}</div>
          </div>
        </div>

        <!-- Level Panel -->
        <div class="sp-card pixel-border">
          <div class="sp-section-header" @click="toggleSection('level')">
            <span class="sp-icon">★</span>
            <span>等级信息</span>
            <span class="sp-arrow" :class="{ expanded: expandedSections.level }">▼</span>
          </div>
          <div v-if="expandedSections.level && summary" class="sp-body">
            <div class="sp-grid">
              <div class="sp-stat-block">
                <div class="sp-stat-num warn">{{ summary.level }}</div>
                <div class="sp-stat-label">当前等级</div>
              </div>
              <div class="sp-stat-block">
                <div class="sp-stat-num primary">{{ summary.total_exp }}</div>
                <div class="sp-stat-label">总经验值</div>
              </div>
            </div>
            <div class="level-mini-bar">
              <div class="lm-track">
                <div class="lm-fill" :style="{ width: expPercent + '%' }"></div>
              </div>
              <div class="lm-label">距下一级 {{ expToNext }} EXP</div>
            </div>
          </div>
        </div>

        <!-- Daily Progress Panel -->
        <div class="sp-card pixel-border">
          <div class="sp-section-header" @click="toggleSection('daily')">
            <span class="sp-icon">▣</span>
            <span>每日任务</span>
            <span class="sp-badge">{{ completedCount }}/{{ summary?.daily_quests.length ?? 0 }}</span>
            <span class="sp-arrow" :class="{ expanded: expandedSections.daily }">▼</span>
          </div>
          <div v-if="expandedSections.daily && summary" class="sp-body">
            <div class="sp-grid">
              <div class="sp-stat-block">
                <div class="sp-stat-num success">{{ completedCount }}</div>
                <div class="sp-stat-label">已完成</div>
              </div>
              <div class="sp-stat-block">
                <div class="sp-stat-num warn">{{ earnedDailyExp }}/{{ totalDailyExp }}</div>
                <div class="sp-stat-label">任务 EXP</div>
              </div>
            </div>
            <div class="status-row">
              <div class="status-row-top">
                <span class="status-dot" style="background: var(--pixel-success)"></span>
                <span class="status-label">完成进度</span>
                <span class="status-count">{{ dailyPercent }}%</span>
              </div>
              <div class="status-track">
                <div class="status-fill" :style="{ width: dailyPercent + '%', background: 'var(--pixel-success)' }"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Achievement Progress Panel -->
        <div class="sp-card pixel-border">
          <div class="sp-section-header" @click="toggleSection('achProgress')">
            <span class="sp-icon">★</span>
            <span>成就进度</span>
            <span class="sp-badge warn">{{ summary?.achievements_completed ?? 0 }}/{{ summary?.achievements_total ?? 0 }}</span>
            <span class="sp-arrow" :class="{ expanded: expandedSections.achProgress }">▼</span>
          </div>
          <div v-if="expandedSections.achProgress && summary" class="sp-body">
            <div class="sp-grid">
              <div class="sp-stat-block">
                <div class="sp-stat-num primary">{{ summary.achievements_completed }}</div>
                <div class="sp-stat-label">已解锁</div>
              </div>
              <div class="sp-stat-block">
                <div class="sp-stat-num warn">{{ unlockedAchExp }}/{{ totalAchExp }}</div>
                <div class="sp-stat-label">成就 EXP</div>
              </div>
            </div>
            <div class="status-row">
              <div class="status-row-top">
                <span class="status-dot" style="background: var(--pixel-warning)"></span>
                <span class="status-label">解锁率</span>
                <span class="status-count">{{ achPercent }}%</span>
              </div>
              <div class="status-track">
                <div class="status-fill" :style="{ width: achPercent + '%', background: 'var(--pixel-warning)' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ====== RIGHT: Quest Content ====== -->
      <div class="q-main">
        <!-- Toolbar -->
        <div class="q-toolbar">
          <div class="toolbar-left">
            <button class="back-btn" @click="router.push('/')">
              <span>◀</span>
              <span>角色信息</span>
            </button>
            <h2 class="q-title">
              <span class="title-icon">▣</span>
              <span>任务系统</span>
              <span class="q-date">{{ todayStr }}</span>
            </h2>
          </div>
          <div class="toolbar-right">
            <button
              class="tab-btn"
              :class="{ active: tab === 'daily' }"
              @click="tab = 'daily'"
            >▣ 每日</button>
            <button
              class="tab-btn"
              :class="{ active: tab === 'achievements' }"
              @click="tab = 'achievements'"
            >★ 成就</button>
          </div>
        </div>

        <!-- Loading -->
        <div v-if="loading" class="loading-state">
          <div class="pixel-loading"></div>
          <span class="loading-text">加载中...</span>
        </div>

        <template v-else-if="summary">
          <!-- Daily Quests Tab -->
          <div v-if="tab === 'daily'" class="quest-cards">
            <div
              v-for="q in summary.daily_quests"
              :key="q.id"
              class="quest-card pixel-border"
              :class="{ completed: q.completed }"
            >
              <div class="qc-status">{{ q.completed ? '✓' : '○' }}</div>
              <div class="qc-content">
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
                    {{ q.completed ? '✓ 已获得' : '+' + q.exp_reward + ' EXP' }}
                  </span>
                </div>
              </div>
            </div>
            <div v-if="summary.daily_quests.length === 0" class="empty-hint">今日暂无任务</div>
          </div>

          <!-- Achievements Tab -->
          <div v-if="tab === 'achievements'" class="ach-cards">
            <div
              v-for="ach in summary.achievements"
              :key="ach.achievement_id"
              class="ach-card pixel-border"
              :class="{ unlocked: ach.unlocked, locked: !ach.unlocked }"
              @mouseenter="onAchHover(ach, $event)"
              @mouseleave="onAchLeave"
            >
              <div class="ac-icon">{{ ach.unlocked ? ach.icon : '?' }}</div>
              <div class="ac-content">
                <div class="ac-name">{{ ach.name }}</div>
                <div class="ac-desc">{{ ach.description }}</div>
                <div class="ac-footer">
                  <span class="ac-exp">+{{ ach.exp_reward }} EXP</span>
                  <span v-if="ach.unlocked && ach.unlocked_at" class="ac-date">
                    {{ ach.unlocked_at.slice(0, 10) }}
                  </span>
                  <span v-else class="ac-locked-text">未解锁</span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Achievement Tooltip (for sidebar) -->
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
</template>

<style scoped>
.quests-page { min-height: 100%; }

.q-layout {
  display: grid;
  grid-template-columns: 1fr 3fr;
  gap: 20px;
  align-items: start;
}

/* ===== Left Sidebar ===== */
.q-sidebar {
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: sticky;
  top: 0;
  overflow-y: auto;
  max-height: calc(100vh - 100px);
}

/* Portrait Card - same as ItemList */
.portrait-card {
  background: var(--pixel-card-bg);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
}

.pc-frame {
  width: 60px;
  height: 78px;
  border: 2px solid var(--pixel-primary);
  background: var(--pixel-bg);
  overflow: hidden;
  flex-shrink: 0;
}

.pc-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  image-rendering: pixelated;
}

.pc-info { display: flex; flex-direction: column; gap: 4px; }

.pc-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  font-weight: 700;
  color: var(--pixel-primary);
}

.pc-level {
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  color: var(--pixel-warning);
  letter-spacing: 0.5px;
}

/* Sidebar Panel Card - same as ItemList */
.sp-card { background: var(--pixel-card-bg); }

.sp-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-text);
  border-bottom: 2px solid var(--pixel-border);
  user-select: none;
  transition: background 0.1s ease;
}

.sp-section-header:hover { background: rgba(65, 166, 246, 0.04); }

.sp-icon {
  font-size: 14px;
  color: var(--pixel-primary);
  width: 18px;
  text-align: center;
}

.sp-arrow {
  margin-left: auto;
  font-size: 8px;
  color: var(--pixel-text-secondary);
  transition: transform 0.2s ease;
}

.sp-arrow.expanded { transform: rotate(180deg); }

.sp-badge {
  margin-left: auto;
  font-size: 10px;
  padding: 1px 6px;
  border: 2px solid var(--pixel-primary);
  color: var(--pixel-primary);
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
}

.sp-badge.warn {
  border-color: var(--pixel-warning);
  color: var(--pixel-warning);
}

.sp-body { padding: 10px 12px; }

.sp-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.sp-stat-block {
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sp-stat-num {
  font-family: 'Press Start 2P', monospace;
  font-size: 11px;
  font-weight: 700;
}

.sp-stat-num.primary { color: var(--pixel-primary); }
.sp-stat-num.warn { color: var(--pixel-warning); }
.sp-stat-num.success { color: var(--pixel-success); }

.sp-stat-label {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

/* Level Mini Bar */
.level-mini-bar { margin-top: 8px; }

.lm-track {
  height: 8px;
  background: var(--pixel-bg-secondary);
  border: 1px solid var(--pixel-border);
  overflow: hidden;
}

.lm-fill {
  height: 100%;
  background: var(--pixel-warning);
  box-shadow: 0 0 4px rgba(239, 125, 87, 0.3);
  transition: width 0.5s ease-out;
}

.lm-label {
  font-size: 10px;
  color: var(--pixel-text-secondary);
  margin-top: 4px;
}

/* Status Row (same as ItemList) */
.status-row { display: flex; flex-direction: column; gap: 3px; margin-top: 8px; }

.status-row-top { display: flex; align-items: center; gap: 6px; }

.status-dot { width: 8px; height: 8px; flex-shrink: 0; }

.status-label {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text);
  flex: 1;
}

.status-count {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

.status-track {
  height: 8px;
  background: var(--pixel-bg);
  border: 1px solid var(--pixel-border);
  overflow: hidden;
}

.status-fill {
  height: 100%;
  transition: width 0.4s ease-out;
}

/* ===== Right Main ===== */
.q-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.q-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-left { display: flex; align-items: center; gap: 12px; }
.toolbar-right { display: flex; align-items: center; gap: 8px; }

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  padding: 6px 12px;
  cursor: pointer;
  box-shadow: 2px 2px 0 var(--pixel-shadow);
  white-space: nowrap;
  transition: border-color 0.12s ease, color 0.12s ease;
}

.back-btn:hover { border-color: var(--pixel-primary); color: var(--pixel-primary); }
.back-btn:active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--pixel-shadow); }

.q-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 14px;
  color: var(--pixel-primary);
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
}

.title-icon { font-size: 18px; }

.q-date {
  font-size: 8px;
  color: var(--pixel-text-secondary);
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
}

/* Tab Buttons */
.tab-btn {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  padding: 6px 14px;
  background: var(--pixel-bg);
  border: 3px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  cursor: pointer;
  transition: border-color 0.12s ease, color 0.12s ease, background 0.12s ease;
  white-space: nowrap;
}

.tab-btn:hover { border-color: var(--pixel-primary); color: var(--pixel-primary); }

.tab-btn.active {
  border-color: var(--pixel-primary);
  color: var(--pixel-primary);
  background: rgba(65, 166, 246, 0.1);
  box-shadow: 0 2px 0 var(--pixel-primary);
}

/* Loading */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 0;
  gap: 16px;
}

.loading-text {
  font-family: 'Press Start 2P', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
}

.empty-hint {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-text-secondary);
  text-align: center;
  padding: 40px 0;
}

/* ===== Daily Quest Cards ===== */
.quest-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quest-card {
  background: var(--pixel-card-bg);
  display: flex;
  gap: 16px;
  padding: 16px 18px;
  transition: border-color 0.12s ease;
}

.quest-card:hover { border-color: var(--pixel-primary); }

.quest-card.completed {
  border-color: var(--pixel-success);
  background: rgba(56, 183, 100, 0.04);
}

.qc-status {
  font-size: 20px;
  color: var(--pixel-border);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding-top: 2px;
}

.quest-card.completed .qc-status { color: var(--pixel-success); }

.qc-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.qc-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 14px;
  font-weight: 700;
  color: var(--pixel-text);
}

.quest-card.completed .qc-name { color: var(--pixel-success); }

.qc-desc {
  font-size: 12px;
  color: var(--pixel-text-secondary);
  line-height: 1.4;
}

.qc-bar-track {
  height: 10px;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  overflow: hidden;
}

.qc-bar-fill {
  height: 100%;
  background: var(--pixel-primary);
  transition: width 0.4s ease-out;
}

.qc-bar-fill.done {
  background: var(--pixel-success);
  box-shadow: 0 0 6px rgba(56, 183, 100, 0.3);
}

.qc-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.qc-progress {
  font-size: 10px;
  color: var(--pixel-text-secondary);
  font-family: 'Press Start 2P', monospace;
}

.qc-exp {
  font-size: 10px;
  color: var(--pixel-warning);
  font-family: 'Press Start 2P', monospace;
}

.qc-exp.earned { color: var(--pixel-success); }

/* ===== Achievement Cards ===== */
.ach-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.ach-card {
  background: var(--pixel-card-bg);
  display: flex;
  gap: 14px;
  padding: 14px 16px;
  align-items: center;
  transition: border-color 0.12s ease, transform 0.08s ease;
}

.ach-card:hover { transform: translateY(-1px); }
.ach-card.locked { opacity: 0.45; }
.ach-card.locked:hover { opacity: 0.6; }

.ach-card.unlocked {
  border-color: var(--pixel-warning);
  box-shadow: 0 0 6px rgba(239, 125, 87, 0.15);
}

.ac-icon {
  font-size: 28px;
  flex-shrink: 0;
  width: 40px;
  text-align: center;
}

.ach-card.locked .ac-icon { color: var(--pixel-border); }

.ac-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.ac-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 13px;
  font-weight: 700;
  color: var(--pixel-text);
}

.ach-card.unlocked .ac-name { color: var(--pixel-warning); }

.ac-desc {
  font-size: 11px;
  color: var(--pixel-text-secondary);
  line-height: 1.3;
}

.ac-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 2px;
}

.ac-exp {
  font-size: 9px;
  color: var(--pixel-primary);
  font-family: 'Press Start 2P', monospace;
}

.ac-date {
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

.ac-locked-text {
  font-size: 10px;
  color: var(--pixel-border);
}

/* Tooltip */
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

.at-desc { font-size: 11px; color: var(--pixel-text); line-height: 1.4; margin-bottom: 4px; }

.at-exp { font-size: 10px; color: var(--pixel-primary); font-family: 'Press Start 2P', monospace; }

.at-date {
  font-size: 9px;
  color: var(--pixel-text-secondary);
  margin-top: 4px;
  padding-top: 4px;
  border-top: 1px solid var(--pixel-border);
}

.at-locked { font-size: 9px; color: var(--pixel-border); margin-top: 4px; }

/* ===== Responsive ===== */
@media (max-width: 900px) {
  .q-layout { grid-template-columns: 1fr; }
  .q-sidebar { position: static; max-height: none; }
}
</style>
