<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import {
  getOverview, getByCategory, getDailyCostRank, getTrends,
  getWarrantyAlerts, getRecentItems,
  type OverviewStats, type CategoryStat, type DailyCostRankItem,
  type MonthlyTrendPoint, type WarrantyAlert, type RecentItem,
} from '../api/stats'
import { formatCurrency } from '../utils/format'

const router = useRouter()

const loading = ref(true)
const overview = ref<OverviewStats | null>(null)
const categoryStats = ref<CategoryStat[]>([])
const costRank = ref<DailyCostRankItem[]>([])
const trends = ref<MonthlyTrendPoint[]>([])
const warrantyAlerts = ref<WarrantyAlert[]>([])
const recentItems = ref<RecentItem[]>([])

// Chart refs
const pieChartRef = ref<HTMLDivElement>()
const trendChartRef = ref<HTMLDivElement>()
const rankChartRef = ref<HTMLDivElement>()

// Pixel theme colors for echarts
const COLORS = ['#41a6f6', '#b13e53', '#38b764', '#ef7d57', '#73eff7', '#ffcd75', '#5d275d', '#182548']

const statusLabel: Record<string, string> = {
  ACTIVE: '使用中', IDLE: '闲置', RETIRED: '退役', SOLD: '已售', DISCARDED: '已弃',
}
const statusColor: Record<string, string> = {
  ACTIVE: 'var(--pixel-success)', IDLE: 'var(--pixel-warning)', RETIRED: 'var(--pixel-text-secondary)',
  SOLD: 'var(--pixel-primary)', DISCARDED: 'var(--pixel-accent)',
}

// Pixel chart theme base config
const pixelTheme = {
  textStyle: { fontFamily: "'Press Start 2P', 'Ark Pixel', monospace", fontSize: 10, color: '#7b8faa' },
  title: { textStyle: { fontFamily: "'Press Start 2P', monospace", fontSize: 12, color: '#f4f4f4' } },
  grid: { top: 36, right: 16, bottom: 28, left: 48, containLabel: false },
}

async function loadAll() {
  loading.value = true
  try {
    const [ov, cat, rank, trend, warranty, recent] = await Promise.all([
      getOverview(), getByCategory(), getDailyCostRank(8),
      getTrends(), getWarrantyAlerts(30), getRecentItems(5),
    ])
    overview.value = ov
    categoryStats.value = cat
    costRank.value = rank
    trends.value = trend
    warrantyAlerts.value = warranty
    recentItems.value = recent
  } catch (e) {
    console.error('Dashboard load error', e)
  } finally {
    loading.value = false
  }
}

function initCharts() {
  if (!loading.value) {
    setTimeout(() => {
      initPieChart()
      initTrendChart()
      initRankChart()
    }, 50)
  }
}

function initPieChart() {
  if (!pieChartRef.value || categoryStats.value.length === 0) return
  const chart = echarts.init(pieChartRef.value)
  chart.setOption({
    ...pixelTheme,
    tooltip: {
      trigger: 'item',
      backgroundColor: '#182548',
      borderColor: '#2e3d62',
      borderWidth: 2,
      textStyle: { color: '#f4f4f4', fontFamily: "'Press Start 2P', monospace", fontSize: 9 },
      formatter: '{b}: {c}件 ({d}%)',
    },
    series: [{
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['50%', '55%'],
      itemStyle: { borderColor: '#0e1225', borderWidth: 2, borderRadius: 0 },
      label: {
        color: '#7b8faa',
        fontSize: 9,
        fontFamily: "'Press Start 2P', monospace",
        formatter: '{b}\n{d}%',
      },
      labelLine: { lineStyle: { color: '#2e3d62', width: 2 } },
      data: categoryStats.value.map((c, i) => ({
        name: c.category_name,
        value: c.item_count,
        itemStyle: { color: c.color || COLORS[i % COLORS.length] },
      })),
    }],
  })
  window.addEventListener('resize', () => chart.resize())
}

function initTrendChart() {
  if (!trendChartRef.value || trends.value.length === 0) return
  const chart = echarts.init(trendChartRef.value)
  const months = trends.value.map(t => t.month.slice(5))
  chart.setOption({
    ...pixelTheme,
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#182548',
      borderColor: '#2e3d62',
      borderWidth: 2,
      textStyle: { color: '#f4f4f4', fontFamily: "'Ark Pixel', monospace", fontSize: 11 },
    },
    xAxis: {
      type: 'category',
      data: months,
      axisLine: { lineStyle: { color: '#2e3d62', width: 2 } },
      axisTick: { show: false },
      axisLabel: { color: '#7b8faa', fontSize: 8, fontFamily: "'Press Start 2P', monospace" },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#141d38', type: [4, 4] } },
      axisLine: { show: false },
      axisLabel: { color: '#7b8faa', fontSize: 8, fontFamily: "'Ark Pixel', monospace", formatter: '¥{value}' },
    },
    series: [{
      type: 'bar',
      data: trends.value.map(t => t.spending),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#41a6f6' },
          { offset: 1, color: '#182548' },
        ]),
        borderColor: '#41a6f6',
        borderWidth: 1,
        borderRadius: 0,
      },
      barWidth: '50%',
    }],
  })
  window.addEventListener('resize', () => chart.resize())
}

function initRankChart() {
  if (!rankChartRef.value || costRank.value.length === 0) return
  const chart = echarts.init(rankChartRef.value)
  const names = costRank.value.map(c => c.name.length > 6 ? c.name.slice(0, 6) + '..' : c.name).reverse()
  const values = costRank.value.map(c => c.daily_cost).reverse()
  chart.setOption({
    ...pixelTheme,
    grid: { ...pixelTheme.grid, left: 72 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#182548',
      borderColor: '#2e3d62',
      borderWidth: 2,
      textStyle: { color: '#f4f4f4', fontFamily: "'Ark Pixel', monospace", fontSize: 11 },
      formatter: (p: any) => `${p[0].name}<br/>日均: ¥${p[0].value.toFixed(2)}`,
    },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#141d38', type: [4, 4] } },
      axisLine: { show: false },
      axisLabel: { color: '#7b8faa', fontSize: 8, fontFamily: "'Ark Pixel', monospace", formatter: '¥{value}' },
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLine: { lineStyle: { color: '#2e3d62', width: 2 } },
      axisTick: { show: false },
      axisLabel: { color: '#f4f4f4', fontSize: 9, fontFamily: "'Ark Pixel', monospace" },
    },
    series: [{
      type: 'bar',
      data: values,
      itemStyle: {
        color: (params: any) => {
          const i = costRank.value.length - 1 - params.dataIndex
          return i < 3 ? '#b13e53' : '#ef7d57'
        },
        borderColor: '#0e1225',
        borderWidth: 1,
        borderRadius: 0,
      },
      barWidth: '55%',
      label: {
        show: true,
        position: 'right',
        color: '#f4f4f4',
        fontSize: 9,
        fontFamily: "'Ark Pixel', monospace",
        formatter: (p: any) => '¥' + p.value.toFixed(2),
      },
    }],
  })
  window.addEventListener('resize', () => chart.resize())
}

function goToItem(id: number) {
  router.push(`/items/${id}`)
}

onMounted(async () => {
  await loadAll()
  initCharts()
})
</script>

<template>
  <div class="dashboard-page animate-fade-in">
    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="pixel-loading"></div>
      <span class="loading-text">加载中...</span>
    </div>

    <template v-else>
      <!-- Section: Stats Overview -->
      <div class="stats-grid stagger-list">
        <div class="stat-card pixel-card-hover">
          <div class="stat-icon">◆</div>
          <div class="stat-info">
            <div class="stat-value">{{ overview?.total_items ?? 0 }}</div>
            <div class="stat-label">物品总数</div>
          </div>
        </div>
        <div class="stat-card accent pixel-card-hover">
          <div class="stat-icon">$</div>
          <div class="stat-info">
            <div class="stat-value">{{ formatCurrency(overview?.total_assets_value ?? 0) }}</div>
            <div class="stat-label">资产总值</div>
          </div>
        </div>
        <div class="stat-card primary pixel-card-hover">
          <div class="stat-icon">◈</div>
          <div class="stat-info">
            <div class="stat-value">{{ formatCurrency(overview?.avg_daily_cost ?? 0) }}</div>
            <div class="stat-label">日均成本</div>
          </div>
        </div>
        <div class="stat-card success pixel-card-hover">
          <div class="stat-icon">▶</div>
          <div class="stat-info">
            <div class="stat-value">{{ overview?.active_items ?? 0 }}</div>
            <div class="stat-label">使用中</div>
          </div>
        </div>
      </div>

      <!-- Section: Charts Row -->
      <div class="charts-row stagger-list">
        <!-- Category Pie -->
        <div class="chart-card pixel-card-hover">
          <h3 class="chart-title">分类统计</h3>
          <div v-if="categoryStats.length === 0" class="chart-empty">暂无数据</div>
          <div v-else ref="pieChartRef" class="chart-container"></div>
        </div>

        <!-- Monthly Trend -->
        <div class="chart-card wide pixel-card-hover">
          <h3 class="chart-title">月度趋势</h3>
          <div v-if="trends.length === 0" class="chart-empty">暂无数据</div>
          <div v-else ref="trendChartRef" class="chart-container"></div>
        </div>
      </div>

      <!-- Section: Bottom Row -->
      <div class="bottom-row stagger-list">
        <!-- Daily Cost Rank -->
        <div class="chart-card pixel-card-hover">
          <h3 class="chart-title">日均成本排行</h3>
          <div v-if="costRank.length === 0" class="chart-empty">暂无数据</div>
          <div v-else ref="rankChartRef" class="chart-container rank-chart"></div>
        </div>

        <!-- Right Column: Alerts + Recent -->
        <div class="side-column">
          <!-- Warranty Alerts -->
          <div class="info-card pixel-card-hover">
            <h3 class="chart-title">
              <span class="title-icon">!</span>
              保修提醒
            </h3>
            <div v-if="warrantyAlerts.length === 0" class="empty-hint">
              <span>暂无提醒</span>
            </div>
            <div v-else class="alert-list">
              <div
                v-for="alert in warrantyAlerts" :key="alert.id"
                class="alert-item pixel-card-hover"
                @click="goToItem(alert.id)"
              >
                <span class="alert-name">{{ alert.name }}</span>
                <span class="alert-days" :class="{ urgent: alert.days_remaining <= 7 }">
                  {{ alert.days_remaining }}天
                </span>
              </div>
            </div>
          </div>

          <!-- Recent Items -->
          <div class="info-card pixel-card-hover">
            <h3 class="chart-title">
              <span class="title-icon">★</span>
              最近物品
            </h3>
            <div v-if="recentItems.length === 0" class="empty-hint">
              <span>暂无物品</span>
            </div>
            <div v-else class="recent-list">
              <div
                v-for="item in recentItems" :key="item.id"
                class="recent-item pixel-card-hover"
                @click="goToItem(item.id)"
              >
                <div class="recent-left">
                  <span class="recent-name">{{ item.name }}</span>
                  <span class="recent-status" :style="{ color: statusColor[item.status] }">
                    {{ statusLabel[item.status] || item.status }}
                  </span>
                </div>
                <span class="recent-cost">{{ formatCurrency(item.daily_cost) }}/天</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
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

/* ===== Stats Grid ===== */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.4);
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}

.stat-card:hover {
  border-color: var(--pixel-text-secondary);
  box-shadow: 4px 6px 0 var(--pixel-shadow);
}

.stat-card:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

.stat-card.accent .stat-icon { color: var(--pixel-accent); }
.stat-card.primary .stat-icon { color: var(--pixel-primary); }
.stat-card.success .stat-icon { color: var(--pixel-success); }

.stat-icon {
  font-family: 'Press Start 2P', monospace;
  font-size: 24px;
  color: var(--pixel-primary);
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
  flex-shrink: 0;
}

.stat-info {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-family: 'Ark Pixel', 'Press Start 2P', monospace;
  font-size: 18px;
  color: var(--pixel-text);
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  animation: pixel-count-up 0.4s ease-out;
}

.stat-label {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  color: var(--pixel-text-secondary);
  letter-spacing: 1px;
  margin-top: 4px;
}

/* ===== Charts ===== */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 16px;
}

.bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-card {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  padding: 16px;
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.4);
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}

.chart-card:hover {
  box-shadow: 4px 6px 0 var(--pixel-shadow);
}

.chart-card.wide {
  /* already handled by grid */
}

.chart-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  color: var(--pixel-text-secondary);
  margin: 0 0 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  color: var(--pixel-warning);
}

.chart-container {
  width: 100%;
  height: 220px;
}

.rank-chart {
  height: 260px;
}

.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 220px;
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  color: var(--pixel-border);
}

/* ===== Side Column ===== */
.side-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-card {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  padding: 16px;
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.4);
  flex: 1;
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}

.info-card:hover {
  border-color: var(--pixel-text-secondary);
}

.empty-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  color: var(--pixel-border);
}

/* Warranty alerts */
.alert-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.alert-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  cursor: pointer;
  transition: border-color 0.12s ease, transform 0.12s ease, background 0.12s ease;
}

.alert-item:hover {
  border-color: var(--pixel-warning);
}

.alert-name {
  font-size: 12px;
  color: var(--pixel-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 60%;
}

.alert-days {
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  color: var(--pixel-warning);
}

.alert-days.urgent {
  color: var(--pixel-accent);
  animation: pixel-blink 0.8s step-end infinite;
}

/* Recent items */
.recent-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.recent-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  cursor: pointer;
  transition: border-color 0.12s ease, transform 0.12s ease, background 0.12s ease;
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
  font-family: 'Press Start 2P', monospace;
  font-size: 7px;
}

.recent-cost {
  font-family: 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-primary);
  white-space: nowrap;
  margin-left: 8px;
}

/* ===== Responsive ===== */
@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .charts-row {
    grid-template-columns: 1fr;
  }
  .bottom-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  .stat-value {
    font-size: 14px;
  }
}
</style>
