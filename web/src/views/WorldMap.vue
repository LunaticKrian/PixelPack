<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useNotifyStore } from '../stores/notification'
import PixelDatePicker from '../components/PixelDatePicker.vue'
import { listTodayIntel, listArchive, getIntelStats, generateIntel } from '../api/intel'
import { REGIONS, type Article, type RegionSlug, type RegionDef, type IntelStats } from '../types/intel'

const notify = useNotifyStore()

// ── state ──
const todayIntel = ref<Article[]>([])
const archive = ref<Article[]>([])
const currentPage = ref(1)
const totalPages = ref(1)
const archiveDates = ref<string[]>([])
const currentDate = ref<string | null>(null)
const stats = ref<IntelStats | null>(null)
const loadingIntel = ref(true)
const loadingArchive = ref(true) // 仅首次挂载：整块替换为 spinner
const navLoading = ref(false)    // 翻页 / 切疆域 / 跳日期：保留旧内容，叠加蒙层，避免抖动
const animateArchive = ref(true) // stagger 入场动画只在首次加载播一次，翻页不再重播（消除闪烁）
const activeRegion = ref<RegionSlug | null>(null)
const selected = ref<Article | null>(null)

// ── 侦测控制台 state ──
const scanning = ref(false)
const scanStatus = ref('')
const scanClock = ref('0:00')
const scanError = ref('')
const scanDoneText = ref('')
let scanTimer: number | undefined
let scanStatusTimer: number | undefined

const todayStr = new Date().toISOString().slice(0, 10)

// ── 派生：每疆域今日未读数（视觉效果） ──
const unreadByRegion = computed(() => {
  const m: Record<string, number> = {}
  todayIntel.value.forEach((a) => {
    m[a.region] = (m[a.region] || 0) + 1
  })
  return m
})

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

// 当前页（一天）标题，如 "2026 · JUL 10"
const dayLabel = computed(() => {
  const iso = currentDate.value
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${y} · ${MONTHS[+m - 1]} ${+d}`
})
// 相邻日期短标签（MM-DD），供翻页器标注目标日
const prevDateShort = computed(() =>
  currentPage.value > 1 ? (archiveDates.value[currentPage.value - 2] || '').slice(5) : '',
)
const nextDateShort = computed(() =>
  currentPage.value < totalPages.value ? (archiveDates.value[currentPage.value] || '').slice(5) : '',
)
function dayOf(iso: string): number {
  return +iso.slice(8, 10)
}
function regionOf(a: Article): RegionDef {
  return REGIONS.find((r) => r.slug === a.region)!
}
const activeRegionDef = computed(() =>
  activeRegion.value ? REGIONS.find((r) => r.slug === activeRegion.value) ?? null : null,
)

// ── 航海日志：加载 / 翻页 / 疆域筛选 / 跳日期（一天一页） ──
// navigation=true：保留旧内容 + 叠加蒙层（翻页/切筛选用，避免抖动）
async function loadArchive(navigation = false) {
  if (navigation) navLoading.value = true
  else loadingArchive.value = true
  try {
    const res = await listArchive(activeRegion.value, currentPage.value)
    archive.value = res.items
    totalPages.value = res.totalPages
    archiveDates.value = res.dates
    currentDate.value = res.date
    if (currentPage.value > res.totalPages && res.totalPages > 0) {
      currentPage.value = res.totalPages
    }
  } catch {
    notify.error('加载航海日志失败')
  } finally {
    loadingArchive.value = false
    navLoading.value = false
    // 首次加载播完 stagger 后关闭，之后翻页不再重播
    if (animateArchive.value) {
      window.setTimeout(() => { animateArchive.value = false }, 500)
    }
  }
}
function selectRegion(slug: RegionSlug | null) {
  activeRegion.value = slug
  currentPage.value = 1 // 切疆域回到第 1 页（最新一天）
  void loadArchive(true)
}
function prevPage() {
  if (currentPage.value <= 1 || navLoading.value) return
  currentPage.value--
  void loadArchive(true)
}
function nextPage() {
  if (currentPage.value >= totalPages.value || navLoading.value) return
  currentPage.value++
  void loadArchive(true)
}
// 选择日期直接跳到那一天（日历 restrict-to-marked，只给可选的真实日期）
function jumpToDate(iso: string | null) {
  if (!iso || iso === currentDate.value || navLoading.value) return
  const idx = archiveDates.value.indexOf(iso)
  if (idx >= 0) {
    currentPage.value = idx + 1
    void loadArchive(true)
  }
}

// ── 信号台刷新（侦测成功后复用） ──
async function refreshToday() {
  try {
    todayIntel.value = await listTodayIntel()
  } catch {
    /* 静默：不打断侦测成功反馈 */
  }
}
async function refreshStats() {
  try {
    stats.value = await getIntelStats()
  } catch {
    /* 静默 */
  }
}

// ── 侦测控制台：主动发起检索 ──
const SCAN_STATUSES = ['调频接收中…', '解析疆域信号…', '归类情报卡…', '归档入库…']
async function triggerScan() {
  if (scanning.value) return
  scanning.value = true
  scanError.value = ''
  scanDoneText.value = ''
  scanStatus.value = SCAN_STATUSES[0]
  let elapsed = 0
  let si = 0
  scanClock.value = '0:00'
  scanTimer = window.setInterval(() => {
    elapsed += 1
    scanClock.value = `${Math.floor(elapsed / 60)}:${(elapsed % 60).toString().padStart(2, '0')}`
  }, 1000)
  scanStatusTimer = window.setInterval(() => {
    si = (si + 1) % SCAN_STATUSES.length
    scanStatus.value = SCAN_STATUSES[si]
  }, 4500)
  try {
    const res = await generateIntel(true)
    scanDoneText.value = `✓ 侦测完成 · 新增 ${res.count} 条情报`
    notify.success(`侦测完成 · 新增 ${res.count} 条情报`)
    void Promise.all([refreshToday(), refreshStats()])
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string }; message?: string }
    const msg = err?.data?.detail || err?.message || '未知错误'
    scanError.value = `✕ 侦测失败 · ${msg}`
    notify.error('侦测失败，稍后再试')
  } finally {
    if (scanTimer !== undefined) window.clearInterval(scanTimer)
    if (scanStatusTimer !== undefined) window.clearInterval(scanStatusTimer)
    scanning.value = false
  }
}

// ── 阅读模态 ──
function openArticle(a: Article) {
  selected.value = a
  document.body.style.overflow = 'hidden'
}
function closeArticle() {
  selected.value = null
  document.body.style.overflow = ''
}
function onOverlayClick(e: MouseEvent) {
  if (e.target === e.currentTarget) closeArticle()
}
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && selected.value) closeArticle()
}

// ── 信号台广播打字机 ──
const TICKER_LINES = [
  '信号台已上线 · 正在接收各疆域广播…',
  '筛选 chips 上的徽标 = 该疆域今日未读数。',
  '今日情报来自 6 个知识疆域的实时聚合。',
  '历史记录可在航海日志中按疆域回溯。',
]
const typed = ref('')
let typer: number | undefined
function startTicker() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    typed.value = TICKER_LINES[0]
    return
  }
  let li = 0
  let ci = 0
  let deleting = false
  const tick = () => {
    const cur = TICKER_LINES[li]
    if (!deleting) {
      ci++
      typed.value = cur.slice(0, ci)
      if (ci >= cur.length) {
        deleting = true
        typer = window.setTimeout(tick, 2000)
        return
      }
    } else {
      ci--
      typed.value = cur.slice(0, ci)
      if (ci <= 0) {
        deleting = false
        li = (li + 1) % TICKER_LINES.length
      }
    }
    typer = window.setTimeout(tick, deleting ? 28 : 55)
  }
  tick()
}
function stopTicker() {
  if (typer !== undefined) window.clearTimeout(typer)
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  startTicker()
  void Promise.all([refreshToday(), refreshStats()])
    .catch(() => notify.error('加载今日情报失败'))
    .finally(() => {
      loadingIntel.value = false
    })
  void loadArchive()
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  stopTicker()
  if (scanTimer !== undefined) window.clearInterval(scanTimer)
  if (scanStatusTimer !== undefined) window.clearInterval(scanStatusTimer)
})
</script>

<template>
  <div class="world-map animate-fade-in">
    <!-- ── 标题铭文 ── -->
    <header class="wm-masthead">
      <div class="header-frame">
        <span class="corner-deco top-left">◆</span>
        <span class="corner-deco top-right">◆</span>
        <div class="header-ornament">✧ ❖ ✧</div>
        <h1 class="wm-title">
          <span class="title-icon animate-float">❖</span>
          世界地图
        </h1>
        <p class="wm-subtitle">— AI 技术情报的每日推送与历史回溯 —</p>
        <span class="corner-deco bottom-left">◆</span>
        <span class="corner-deco bottom-right">◆</span>
      </div>
    </header>

    <!-- ════ ACT 1 · 信号台 / 每日推送 ════ -->
    <section class="signal-panel">
      <div class="sig-head">
        <span class="sig-live"><span class="sig-live-dot"></span>ON AIR</span>
        <span class="sig-bars" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <span class="sig-name">◉ 信号台</span>
        <span class="sig-date">{{ todayStr }} · 07:00</span>
      </div>

      <div class="sig-ticker">
        <span class="sig-prompt">&gt; BROADCAST_</span>
        <span class="sig-typed">{{ typed }}</span>
        <span class="sig-caret"></span>
      </div>

      <div class="sig-stats">
        <div class="stat-tile">
          <div class="stat-label">今日推送</div>
          <div class="stat-value hi">{{ stats?.todayCount ?? '—' }}</div>
        </div>
        <div class="stat-tile">
          <div class="stat-label">本周累计</div>
          <div class="stat-value">{{ stats?.weekCount ?? '—' }}</div>
        </div>
        <div class="stat-tile">
          <div class="stat-label">已归档</div>
          <div class="stat-value">{{ stats?.archivedCount ?? '—' }}</div>
        </div>
        <div class="stat-tile">
          <div class="stat-label">待读</div>
          <div class="stat-value hi">{{ stats?.unreadCount ?? '—' }}</div>
        </div>
      </div>

      <div class="sig-body">
        <div class="sec-title">
          <span class="sec-gly">▶</span> 今日情报
          <span class="sec-tag">TODAY · INCOMING</span>
        </div>

        <div v-if="loadingIntel" class="loading-state">
          <div class="pixel-loading"></div>
          <p class="loading-text">接收信号中...</p>
        </div>

        <div v-else class="broadcast stagger-list">
          <article
            v-for="a in todayIntel"
            :key="a.id"
            class="intel pixel-card-hover"
            :style="{ '--reg-c': regionOf(a).color }"
            @click="openArticle(a)"
          >
            <span class="intel-unread" aria-label="未读"></span>
            <div class="intel-top">
              <span class="intel-reg">{{ regionOf(a).code }} · {{ regionOf(a).name }}</span>
              <span class="intel-src">{{ a.source }}</span>
            </div>
            <div class="intel-title">{{ a.title }}</div>
            <div class="intel-sum">{{ a.summary }}</div>
            <div class="intel-foot">
              <span>⌖ {{ a.readTime }}</span>
              <span>· 今日</span>
              <span class="intel-cta">调频阅读 ▸</span>
            </div>
          </article>
        </div>
      </div>

      <!-- 侦测控制台 · 主动发起检索 -->
      <div class="sig-console">
        <div class="radar" :class="{ 'is-sweeping': scanning }" aria-hidden="true">
          <span class="radar-ring r1"></span>
          <span class="radar-ring r2"></span>
          <span class="radar-core"></span>
          <span class="radar-sweep"></span>
        </div>
        <button class="scan-btn" :disabled="scanning" @click="triggerScan">
          <span class="scan-ico">{{ scanning ? '◉' : '⚡' }}</span>
          {{ scanning ? '侦测中…' : '发起侦测' }}
        </button>
        <div class="scan-status">
          <span v-if="scanning" class="scan-busy">
            {{ scanStatus }} <b class="scan-time">{{ scanClock }}</b>
          </span>
          <span v-else-if="scanError" class="scan-err">{{ scanError }}</span>
          <span v-else class="scan-idle">{{ scanDoneText || '侦测就绪 · 可手动发起一次情报侦测' }}</span>
        </div>
      </div>
    </section>

    <!-- ════ ACT 2 · 航海日志 / 历史查看 ════ -->
    <section class="voyage-panel">
      <div class="voyage-head">
        <span class="voyage-name">▤ 航海日志 · ARCHIVE</span>
        <span class="voyage-meta">{{
          activeRegionDef
            ? `${activeRegionDef.name} · 共 ${totalPages} 天`
            : `共 ${totalPages} 天记录`
        }}</span>
      </div>

      <!-- 疆域筛选（含未读徽标） -->
      <div class="vfilters">
        <button class="vchip" :class="{ 'is-active': !activeRegion }" @click="selectRegion(null)">
          <span class="vchip-dot vchip-dot--all"></span>
          全部
        </button>
        <button
          v-for="region in REGIONS"
          :key="region.id"
          class="vchip"
          :class="{ 'is-active': activeRegion === region.slug }"
          @click="selectRegion(region.slug)"
        >
          <span class="vchip-dot" :style="{ background: region.color }"></span>
          {{ region.name }}
          <span v-if="unreadByRegion[region.slug]" class="vchip-unread">{{ unreadByRegion[region.slug] }}</span>
        </button>
      </div>

      <div class="voyage-body">
        <div v-if="loadingArchive" class="loading-state">
          <div class="pixel-loading"></div>
          <p class="loading-text">翻开航海日志...</p>
        </div>

        <div v-else class="archive-wrap">
          <template v-if="archive.length">
            <div class="day-head">
              ▣ {{ dayLabel }} <span class="day-count">{{ archive.length }} 篇</span>
            </div>
            <div class="archive-grid" :class="{ 'stagger-list': animateArchive }">
              <article
                v-for="a in archive"
                :key="a.id"
                class="log-card pixel-card-hover"
                :style="{ '--reg-c': regionOf(a).color }"
                @click="openArticle(a)"
              >
                <div class="log-date">
                  <div class="log-day">{{ dayOf(a.publishedAt) }}</div>
                  <div class="log-mon">{{ MONTHS[+a.publishedAt.slice(5, 7) - 1] }}</div>
                </div>
                <div class="log-body">
                  <div class="log-top">
                    <span class="log-reg">{{ regionOf(a).name }}</span>
                    <span class="log-time">⌖ {{ a.readTime }}</span>
                  </div>
                  <div class="log-title">{{ a.title }}</div>
                  <div class="log-src">来源 · {{ a.source }}</div>
                </div>
              </article>
            </div>
          </template>
          <!-- 翻页/切筛选用蒙层：保留旧内容高度，消除抖动 -->
          <div v-if="navLoading" class="nav-overlay">
            <div class="pixel-loading"></div>
          </div>
        </div>
      </div>

      <div class="pager">
        <button class="pager-btn" :disabled="currentPage <= 1 || navLoading" @click="prevPage">
          ◀ {{ prevDateShort || '最新' }}
        </button>
        <span>第 <b class="t-gold">{{ currentPage }}</b> / {{ totalPages || 1 }} 天</span>
        <button class="pager-btn" :disabled="currentPage >= totalPages || navLoading" @click="nextPage">
          {{ nextDateShort || '更早' }} ▶
        </button>
        <PixelDatePicker
          class="pager-date"
          :model-value="currentDate || todayStr"
          :marked-dates="archiveDates"
          :restrict-to-marked="archiveDates.length > 0"
          :drop-up="true"
          :width="'132px'"
          placeholder="引用日期"
          @update:model-value="jumpToDate"
        />
      </div>
    </section>

    <!-- ════ 阅读模态 ════ -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="selected" class="reader-overlay" @click="onOverlayClick">
          <div class="reader-modal pixel-border animate-scale-in">
            <div class="reader-topbar">
              <span class="reader-reg" :style="{ background: regionOf(selected).color }">
                {{ regionOf(selected).code }} {{ regionOf(selected).name }}
              </span>
              <span class="reader-date">{{ selected.publishedAt }} · ⌖ {{ selected.readTime }}</span>
              <button class="reader-close" @click="closeArticle">✕</button>
            </div>
            <div class="reader-body">
              <h2 class="reader-title">{{ selected.title }}</h2>
              <p v-if="selected.summary" class="reader-summary">{{ selected.summary }}</p>
              <div class="reader-content">{{ selected.body }}</div>
              <a
                v-if="selected.url"
                class="reader-link"
                :href="selected.url"
                target="_blank"
                rel="noopener"
              >阅读原文 ▸</a>
              <hr class="pixel-divider" />
              <div class="reader-end">END OF TRANSMISSION</div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════════
   世界地图模块 — 复用 web 工程 --pixel-* 主题变量
   ═══════════════════════════════════════════════ */
.world-map {
  --wm-line-dim: color-mix(in srgb, var(--pixel-border) 55%, transparent);
  --wm-faint: color-mix(in srgb, var(--pixel-text-secondary) 60%, transparent);
  --wm-beacon: var(--pixel-warning);
  --wm-inset: var(--pixel-bg);

  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 1180px;
  margin: 0 auto;
}

/* ── 标题铭文 ── */
.wm-masthead {
  display: flex;
  justify-content: center;
  padding-top: 4px;
}
.header-frame {
  position: relative;
  text-align: center;
  padding: 18px 40px;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg-secondary);
  box-shadow: 4px 4px 0 var(--pixel-shadow), inset 0 0 40px rgba(65, 166, 246, 0.03);
}
.corner-deco {
  position: absolute;
  font-size: 6px;
  color: var(--pixel-primary);
  opacity: 0.5;
  line-height: 1;
}
.corner-deco.top-left { top: 6px; left: 8px; }
.corner-deco.top-right { top: 6px; right: 8px; }
.corner-deco.bottom-left { bottom: 6px; left: 8px; }
.corner-deco.bottom-right { bottom: 6px; right: 8px; }
.header-ornament {
  font-size: 8px;
  color: var(--pixel-primary);
  letter-spacing: 6px;
  opacity: 0.4;
}
.wm-title {
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 15px;
  color: var(--pixel-primary);
  margin: 10px 0 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  text-shadow: 0 0 12px rgba(65, 166, 246, 0.3);
}
.title-icon { font-size: 18px; color: var(--pixel-info); }
.wm-subtitle {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
  margin: 0;
  letter-spacing: 2px;
}

/* ── 通用面板 ── */
.signal-panel,
.voyage-panel {
  border: 3px solid var(--pixel-border);
  background: var(--pixel-card-bg);
  box-shadow: 0 0 0 3px var(--pixel-bg), 4px 4px 0 var(--pixel-shadow);
}

.sec-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-weight: 700;
  font-size: 13px;
  color: var(--pixel-text);
  letter-spacing: 1px;
  margin-bottom: 12px;
}
.sec-gly { color: var(--pixel-primary); }
.sec-tag {
  margin-left: auto;
  font-size: 8px;
  color: var(--wm-faint);
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px 0;
}
.loading-text {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
  margin: 0;
}

/* ════ ACT 1 · 信号台 ════ */
.signal-panel {
  position: relative;
  overflow: hidden;
}
.signal-panel::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  height: 80px;
  top: -80px;
  background: linear-gradient(180deg, transparent, rgba(65, 166, 246, 0.08), transparent);
  animation: sig-sweep 5.5s linear infinite;
  pointer-events: none;
  z-index: 1;
}
@keyframes sig-sweep {
  from { top: -80px; }
  to { top: 100%; }
}

.sig-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  background: var(--pixel-bg-secondary);
  border-bottom: 2px solid var(--pixel-border);
  position: relative;
  z-index: 2;
}
.sig-live {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 9px;
  color: var(--pixel-accent);
}
.sig-live-dot {
  width: 8px;
  height: 8px;
  background: var(--pixel-accent);
  animation: pixel-blink 1s step-end infinite;
}
.sig-bars {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 15px;
}
.sig-bars i {
  width: 3px;
  background: var(--pixel-success);
}
.sig-bars i:nth-child(1) { height: 5px; }
.sig-bars i:nth-child(2) { height: 9px; }
.sig-bars i:nth-child(3) { height: 12px; background: var(--pixel-primary); }
.sig-bars i:nth-child(4) { height: 15px; background: var(--pixel-primary); }
.sig-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 13px;
  font-weight: 700;
  color: var(--pixel-text);
}
.sig-date {
  margin-left: auto;
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 9px;
  color: var(--pixel-text-secondary);
}

.sig-ticker {
  padding: 11px 14px;
  background: var(--wm-inset);
  border-bottom: 2px solid var(--pixel-border);
  min-height: 40px;
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  z-index: 2;
}
.sig-prompt {
  color: var(--pixel-warning);
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 9px;
  flex-shrink: 0;
}
.sig-typed {
  font-size: 13px;
  color: var(--pixel-primary);
  min-height: 18px;
}
.sig-caret {
  display: inline-block;
  width: 7px;
  height: 14px;
  background: var(--pixel-primary);
  vertical-align: -2px;
  animation: pixel-blink 1s step-end infinite;
}

.sig-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 2px solid var(--pixel-border);
}
.stat-tile {
  padding: 12px;
  background: var(--pixel-bg-secondary);
  border: 2px solid var(--pixel-border);
}
.stat-label {
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 8px;
  color: var(--pixel-text-secondary);
}
.stat-value {
  margin-top: 6px;
  font-family: var(--font-pixel-num), 'VT323', monospace;
  font-size: 22px;
  color: var(--pixel-text);
  line-height: 1;
}
.stat-value.hi { color: var(--pixel-warning); }

.sig-body {
  padding: 14px;
  position: relative;
  z-index: 2;
}
.broadcast {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

/* 情报卡 */
.intel {
  position: relative;
  padding: 12px;
  background: var(--pixel-bg-secondary);
  border: 2px solid var(--pixel-border);
  display: flex;
  flex-direction: column;
  gap: 8px;
  cursor: pointer;
}
.intel-unread {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 11px;
  height: 11px;
  background: var(--wm-beacon);
  border: 2px solid var(--pixel-bg);
  box-shadow: 0 0 6px 1px rgba(239, 125, 87, 0.6);
  animation: pixel-blink 1.2s step-end infinite;
  z-index: 3;
}
.intel-top {
  display: flex;
  align-items: center;
  gap: 6px;
}
.intel-reg {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 8px;
  padding: 2px 6px;
  border: 2px solid var(--pixel-bg);
  background: var(--wm-inset);
  color: var(--reg-c, var(--pixel-primary));
  white-space: nowrap;
}
.intel-src {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 10px;
  color: var(--wm-faint);
  margin-left: auto;
}
.intel-title {
  font-weight: 700;
  font-size: 14px;
  line-height: 1.35;
  color: var(--pixel-text);
}
.intel-sum {
  font-size: 12px;
  color: var(--pixel-text-secondary);
  line-height: 1.5;
}
.intel-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
  padding-top: 9px;
  border-top: 1px solid var(--wm-line-dim);
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 8px;
  color: var(--wm-faint);
}
.intel-cta {
  margin-left: auto;
  color: var(--pixel-primary);
}

/* ════ ACT 2 · 航海日志 ════ */
.voyage-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 2px solid var(--pixel-border);
  background: var(--pixel-bg-secondary);
  flex-wrap: wrap;
}
.voyage-name {
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 10px;
  color: var(--pixel-primary);
}
.voyage-meta {
  margin-left: auto;
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 8px;
  color: var(--pixel-text-secondary);
}

/* 疆域筛选 chips（含未读徽标） */
.vfilters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 12px;
  border-bottom: 2px solid var(--pixel-border);
}
.vchip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 11px;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  font-weight: 700;
  color: var(--pixel-text-secondary);
  background: var(--pixel-bg-secondary);
  border: 2px solid var(--pixel-border);
  cursor: pointer;
  transition: color 0.1s ease, border-color 0.1s ease, background 0.1s ease;
}
.vchip:hover {
  color: var(--pixel-text);
  border-color: var(--pixel-text-secondary);
}
.vchip.is-active {
  color: var(--pixel-text);
  background: color-mix(in srgb, var(--pixel-primary) 16%, transparent);
  border-color: var(--pixel-primary);
  box-shadow: 0 2px 0 var(--pixel-primary);
}
.vchip-dot {
  width: 9px;
  height: 9px;
  border: 1px solid var(--pixel-bg);
  flex-shrink: 0;
}
.vchip-dot--all {
  background: repeating-linear-gradient(45deg, var(--pixel-text-secondary) 0 2px, transparent 2px 4px);
}
.vchip-unread {
  min-width: 15px;
  height: 15px;
  padding: 0 3px;
  display: inline-grid;
  place-items: center;
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 7px;
  color: var(--pixel-bg);
  background: var(--wm-beacon);
  border: 1px solid var(--pixel-bg);
  margin-left: 2px;
}

.voyage-body { padding: 14px; }

.archive-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

/* 翻页/切筛选时保留旧内容 + 蒙层，避免高度塌陷造成抖动 */
.archive-wrap {
  position: relative;
  min-height: 180px;
}
.nav-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--pixel-bg) 72%, transparent);
  backdrop-filter: blur(1px);
  z-index: 4;
}

/* 历史条目卡 */
.log-card {
  position: relative;
  padding: 11px 12px;
  background: var(--pixel-bg-secondary);
  border: 2px solid var(--pixel-border);
  display: flex;
  gap: 11px;
  cursor: pointer;
}
.log-date {
  flex-shrink: 0;
  width: 42px;
  text-align: center;
  padding: 5px 2px;
  background: var(--wm-inset);
  border: 2px solid var(--pixel-bg);
  box-shadow: inset 1px 1px 0 rgba(0, 0, 0, 0.3);
  align-self: flex-start;
}
.log-day {
  font-family: var(--font-pixel-num), 'VT323', monospace;
  font-size: 18px;
  color: var(--pixel-primary);
  line-height: 1;
}
.log-mon {
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 6px;
  color: var(--wm-faint);
  margin-top: 3px;
  letter-spacing: 0.5px;
}
.log-body { flex: 1; min-width: 0; }
.log-top {
  display: flex;
  align-items: center;
  gap: 6px;
}
.log-reg {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 7px;
  color: var(--reg-c, var(--pixel-primary));
}
.log-reg::before {
  content: '';
  width: 7px;
  height: 7px;
  background: var(--reg-c, var(--pixel-primary));
  border: 1px solid var(--pixel-bg);
}
.log-time {
  margin-left: auto;
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 7px;
  color: var(--wm-faint);
}
.log-title {
  font-weight: 700;
  font-size: 13px;
  line-height: 1.3;
  margin-top: 5px;
  color: var(--pixel-text);
}
.log-src {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 10px;
  color: var(--wm-faint);
  margin-top: 6px;
}

/* 分页 */
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 4px 0 14px;
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 9px;
  color: var(--pixel-text-secondary);
}
.pager b { font-weight: 400; }
.t-gold { color: var(--pixel-warning); }
.pager-btn {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  padding: 4px 10px;
  color: var(--pixel-text-secondary);
  background: var(--pixel-bg-secondary);
  border: 2px solid var(--pixel-border);
  cursor: pointer;
  transition: color 0.1s ease, border-color 0.1s ease;
}
.pager-btn:hover {
  color: var(--pixel-primary);
  border-color: var(--pixel-primary);
}
.pager-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.pager-btn:disabled:hover {
  color: var(--pixel-text-secondary);
  border-color: var(--pixel-border);
}

/* 日期跳转（复用 PixelDatePicker，与翻页按钮等高对齐，向上展开） */
.pager-date {
  margin-left: 4px;
}
.pager-date :deep(.px-date-trigger) {
  padding: 3px 8px;
  border-width: 2px;
  font-size: 11px;
  justify-content: center;
}
.pager-date :deep(.px-date-icon) {
  font-size: 11px;
}

/* ════ 侦测控制台 · 主动发起检索 ════ */
.sig-console {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border-top: 2px solid var(--pixel-border);
  background: var(--pixel-bg-secondary);
}
.radar {
  position: relative;
  width: 50px;
  height: 50px;
  flex-shrink: 0;
  border: 2px solid var(--pixel-border);
  background: var(--wm-inset);
  border-radius: 50%;
  overflow: hidden;
}
.radar-core {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 6px;
  height: 6px;
  background: var(--pixel-success);
  border-radius: 50%;
  transform: translate(-50%, -50%);
}
.radar-ring {
  position: absolute;
  left: 50%;
  top: 50%;
  border: 1px solid var(--wm-line-dim);
  border-radius: 50%;
  transform: translate(-50%, -50%);
}
.radar-ring.r1 { width: 26px; height: 26px; }
.radar-ring.r2 { width: 40px; height: 40px; }
.radar-sweep {
  position: absolute;
  inset: 0;
  background: conic-gradient(
    from 0deg,
    transparent 0deg 300deg,
    color-mix(in srgb, var(--pixel-primary) 45%, transparent) 360deg
  );
  opacity: 0;
}
.radar.is-sweeping .radar-sweep {
  opacity: 1;
  animation: radar-rot 1.6s linear infinite;
}
.radar.is-sweeping .radar-core {
  animation: radar-ping 1.6s ease-out infinite;
}
@keyframes radar-rot {
  to { transform: rotate(360deg); }
}
@keyframes radar-ping {
  0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--pixel-primary) 50%, transparent); }
  100% { box-shadow: 0 0 0 13px transparent; }
}
.scan-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-weight: 700;
  font-size: 13px;
  padding: 8px 16px;
  color: var(--pixel-bg);
  background: var(--pixel-primary);
  border: 2px solid var(--pixel-text);
  box-shadow: 3px 3px 0 var(--pixel-shadow);
  cursor: pointer;
  transition: transform 0.08s ease, box-shadow 0.08s ease;
  flex-shrink: 0;
}
.scan-btn:hover:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 var(--pixel-shadow);
}
.scan-btn:active:not(:disabled) {
  transform: translate(3px, 3px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}
.scan-btn:disabled {
  opacity: 0.6;
  cursor: progress;
  background: var(--pixel-text-secondary);
  box-shadow: none;
}
.scan-ico { font-size: 14px; }
.scan-status {
  flex: 1;
  min-width: 0;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  line-height: 1.5;
}
.scan-idle { color: var(--pixel-text-secondary); }
.scan-busy { color: var(--pixel-primary); }
.scan-busy .scan-time {
  margin-left: 6px;
  font-family: var(--font-pixel-num), 'VT323', monospace;
  color: var(--pixel-warning);
}
.scan-err { color: var(--pixel-accent); }

/* 单日头 */
.day-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 9px;
  color: var(--pixel-warning);
  letter-spacing: 1px;
}
.day-head::after {
  content: '';
  flex: 1;
  height: 2px;
  background: repeating-linear-gradient(90deg, var(--pixel-border) 0 6px, transparent 6px 10px);
}
.day-count { color: var(--wm-faint); font-size: 8px; }

/* ════ 阅读模态 ════ */
.reader-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 32px 16px;
  background: rgba(0, 0, 0, 0.72);
  overflow-y: auto;
}
.reader-modal {
  position: relative;
  width: 100%;
  max-width: 680px;
  background: var(--pixel-card-bg);
  margin: auto 0;
}
.reader-topbar {
  position: sticky;
  top: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 2px solid var(--pixel-border);
  background: var(--pixel-bg-secondary);
}
.reader-reg {
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 8px;
  color: var(--pixel-bg);
  padding: 2px 8px;
  border: 2px solid var(--pixel-text);
}
.reader-date {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
}
.reader-close {
  margin-left: auto;
  font-size: 13px;
  padding: 3px 9px;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
  color: var(--pixel-text-secondary);
  cursor: pointer;
  transition: color 0.1s ease, border-color 0.1s ease;
}
.reader-close:hover {
  color: var(--pixel-accent);
  border-color: var(--pixel-accent);
}
.reader-body {
  max-height: calc(90vh - 60px);
  overflow-y: auto;
  padding: 20px 24px 24px;
}
.reader-title {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 17px;
  font-weight: 700;
  color: var(--pixel-text);
  margin: 0 0 12px;
  line-height: 1.4;
}
.reader-summary {
  font-size: 13px;
  color: var(--pixel-primary);
  line-height: 1.6;
  margin: 0 0 16px;
  border-left: 3px solid var(--pixel-primary);
  padding-left: 12px;
}
.reader-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--pixel-text);
  white-space: pre-line;
}
.reader-link {
  display: inline-block;
  margin-top: 16px;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-primary);
  border-bottom: 1px solid color-mix(in srgb, var(--pixel-primary) 40%, transparent);
  text-decoration: none;
}
.reader-end {
  margin-top: 14px;
  text-align: center;
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 8px;
  color: var(--wm-faint);
  letter-spacing: 2px;
}

/* ════ 响应式 ════ */
@media (max-width: 768px) {
  .sig-stats { grid-template-columns: repeat(2, 1fr); }
  .broadcast,
  .archive-grid { grid-template-columns: 1fr; }
  .voyage-meta { width: 100%; margin-left: 0; }
  .reader-modal { max-width: 100%; }
}
@media (max-width: 768px) {
  .sig-console { flex-wrap: wrap; }
  .scan-status { width: 100%; }
}
@media (prefers-reduced-motion: reduce) {
  .radar.is-sweeping .radar-sweep,
  .radar.is-sweeping .radar-core { animation: none; }
}
</style>
