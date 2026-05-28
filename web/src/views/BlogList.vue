<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'
import '../styles/blog-content.css'
import { listBlogs, deleteBlog } from '../api/journals'
import type { Blog } from '../types/journal'
import { useNotifyStore } from '../stores/notification'

const router = useRouter()
const notify = useNotifyStore()

const blogs = ref<Blog[]>([])
const loading = ref(true)
const detailBlog = ref<Blog | null>(null)

async function loadBlogs() {
  loading.value = true
  try {
    blogs.value = await listBlogs()
  } catch {
    notify.error('加载博客失败')
  } finally {
    loading.value = false
  }
}

function openDetail(blog: Blog) {
  detailBlog.value = blog
  document.body.style.overflow = 'hidden'
}

function closeDetail() {
  detailBlog.value = null
  document.body.style.overflow = ''
}

async function handleDelete(id: number) {
  try {
    await deleteBlog(id)
    blogs.value = blogs.value.filter(b => b.id !== id)
    if (detailBlog.value?.id === id) closeDetail()
    notify.success('已删除')
  } catch {
    notify.error('删除失败')
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}

function copyShareLink(token: string) {
  const url = `${window.location.origin}/share/${token}`
  navigator.clipboard.writeText(url)
  notify.success('分享链接已复制')
}

function onOverlayClick(e: MouseEvent) {
  if (e.target === e.currentTarget) closeDetail()
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && detailBlog.value) closeDetail()
}

onMounted(() => {
  loadBlogs()
  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="chronicle animate-fade-in">
    <!-- Chronicle Header -->
    <header class="chronicle-header">
      <div class="header-frame">
        <div class="corner-deco top-left">◆</div>
        <div class="corner-deco top-right">◆</div>
        <div class="header-ornament">✧ ✦ ✧</div>
        <h1 class="chronicle-title">
          <span class="title-icon animate-float">◈</span>
          旅行日志
        </h1>
        <p class="chronicle-subtitle">— 记录每一段冒险的足迹 —</p>
        <div class="header-ornament bottom">✧ ✦ ✧</div>
        <div class="corner-deco bottom-left">◆</div>
        <div class="corner-deco bottom-right">◆</div>
      </div>
      <button class="quest-new-btn pixel-btn-glow" @click="router.push('/blog/new')">
        <span class="btn-icon">◈</span> 记录新旅程
      </button>
    </header>

    <!-- Journey Stats -->
    <div class="journey-stats">
      <div class="tab-count">
        共 <span class="count-num">{{ blogs.length }}</span> 段旅程
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="pixel-loading"></div>
      <p class="loading-text">翻开旅途中...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="blogs.length === 0" class="empty-chronicle">
      <div class="empty-scroll">
        <div class="scroll-top"></div>
        <div class="scroll-body">
          <div class="empty-map">
            <div class="map-path-start"></div>
            <div class="map-compass">◇</div>
            <div class="map-question animate-float">?</div>
          </div>
          <p class="empty-title">前方的道路尚未踏足</p>
          <p class="empty-desc">拿起你的笔，开始记录第一段冒险吧</p>
          <button class="quest-new-btn pixel-btn-glow" @click="router.push('/blog/new')">
            <span class="btn-icon">◈</span> 踏上旅途
          </button>
        </div>
        <div class="scroll-bottom"></div>
      </div>
    </div>

    <!-- Journey Timeline -->
    <div v-else class="journey-timeline stagger-list">
      <div class="timeline-path"></div>
      <div class="timeline-start-marker">
        <span class="marker-diamond animate-float">◇</span>
      </div>

      <div
        v-for="(blog, index) in blogs"
        :key="blog.id"
        class="milestone"
        :class="[index % 2 === 0 ? 'milestone-left' : 'milestone-right']"
        :style="{ animationDelay: `${index * 0.06}s` }"
      >
        <!-- Waypoint Node -->
        <div class="waypoint-node" :class="{ published: blog.status === 'published' }">
          <span class="waypoint-icon">{{ blog.status === 'draft' ? '◇' : '✦' }}</span>
        </div>

        <!-- Connection Line -->
        <div class="connection-line"></div>

        <!-- Milestone Card -->
        <div
          class="milestone-card pixel-border pixel-card-hover"
          @click="openDetail(blog)"
        >
          <!-- Card Header Bar -->
          <div class="card-header-bar">
            <span class="quest-status" :class="blog.status">
              {{ blog.status === 'draft' ? '◈ 草稿中' : '✦ 已完成' }}
            </span>
            <span class="quest-date">{{ formatDate(blog.created_at) }}</span>
          </div>

          <!-- Card Content -->
          <div class="card-content">
            <!-- Cover Thumbnail -->
            <div v-if="blog.cover_url" class="card-cover-frame">
              <img :src="blog.cover_url" alt="" class="cover-thumb" />
              <div class="cover-frame-corner tl"></div>
              <div class="cover-frame-corner tr"></div>
              <div class="cover-frame-corner bl"></div>
              <div class="cover-frame-corner br"></div>
            </div>

            <div class="card-text">
              <h2 class="quest-title">{{ blog.title }}</h2>
              <p v-if="blog.summary" class="quest-summary">{{ blog.summary }}</p>
              <div v-if="blog.tags.length" class="quest-attrs">
                <span v-for="tag in blog.tags.slice(0, 4)" :key="tag" class="attr-tag">{{ tag }}</span>
              </div>
            </div>
          </div>

          <!-- Card Footer -->
          <div class="card-footer-bar">
            <span class="chapter-num">CH.{{ String(index + 1).padStart(2, '0') }}</span>
            <div class="card-actions">
              <button v-if="blog.share_token" class="action-btn" @click.stop="copyShareLink(blog.share_token)" title="复制分享链接">⎘</button>
              <button class="action-btn" @click.stop="router.push(`/blog/${blog.id}/edit`)" title="编辑">✎</button>
              <button class="action-btn danger" @click.stop="handleDelete(blog.id)" title="删除">✕</button>
            </div>
          </div>

          <!-- Decorative corner -->
          <span class="card-corner-deco">◆</span>
        </div>
      </div>

      <!-- Path Continues -->
      <div class="timeline-end-marker">
        <div class="path-continues">
          <div class="continues-dots">
            <span>·</span><span>·</span><span>·</span>
          </div>
          <span class="continues-text">旅途仍在继续</span>
          <div class="continues-dots">
            <span>·</span><span>·</span><span>·</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Detail Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="detailBlog" class="detail-overlay" @click="onOverlayClick">
          <div class="detail-modal pixel-border animate-scale-in">
            <!-- Modal Header -->
            <div class="modal-top-bar">
              <button class="modal-close-btn" @click="closeDetail">✕</button>
              <div class="modal-actions">
                <button v-if="detailBlog.share_token" class="modal-action-btn" @click="copyShareLink(detailBlog.share_token)">⎘ 分享</button>
                <button class="modal-action-btn" @click="router.push(`/blog/${detailBlog.id}/edit`); closeDetail()">✎ 编辑</button>
                <button class="modal-action-btn danger" @click="handleDelete(detailBlog.id)">✕ 删除</button>
              </div>
            </div>

            <!-- Modal Body -->
            <div class="modal-body">
              <!-- Cover -->
              <div v-if="detailBlog.cover_url" class="modal-cover">
                <img :src="detailBlog.cover_url" alt="" />
                <div class="modal-cover-fade"></div>
              </div>

              <!-- Header -->
              <div class="modal-header" :class="{ 'no-cover': !detailBlog.cover_url }">
                <div class="modal-meta-row">
                  <span class="modal-status" :class="detailBlog.status">
                    {{ detailBlog.status === 'draft' ? '◈ 草稿中' : '✦ 已完成' }}
                  </span>
                  <span class="modal-date">{{ formatDate(detailBlog.created_at) }}</span>
                </div>
                <h1 class="modal-title">{{ detailBlog.title }}</h1>
                <p v-if="detailBlog.summary" class="modal-summary">{{ detailBlog.summary }}</p>
                <div v-if="detailBlog.tags.length" class="modal-tags">
                  <span v-for="tag in detailBlog.tags" :key="tag" class="modal-tag">{{ tag }}</span>
                </div>
              </div>

              <hr class="pixel-divider" style="margin: 0 24px;" />

              <!-- Content -->
              <div class="modal-content blog-scroll-content">
                <MdPreview :model-value="detailBlog.content || ''" />
              </div>
            </div>

            <!-- Corner decorations -->
            <span class="modal-corner tl">◆</span>
            <span class="modal-corner tr">◆</span>
            <span class="modal-corner bl">◆</span>
            <span class="modal-corner br">◆</span>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════════
   Journey Chronicle — RPG Quest Journal Timeline
   ═══════════════════════════════════════════════ */

@keyframes chronicle-fade-in {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes milestone-enter-left {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes milestone-enter-right {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes marker-pulse {
  0%, 100% { transform: scale(1); opacity: 0.8; }
  50% { transform: scale(1.15); opacity: 1; }
}

@keyframes path-flow {
  from { background-position: 0 0; }
  to { background-position: 0 12px; }
}

.chronicle {
  display: flex;
  flex-direction: column;
  gap: 24px;
  animation: chronicle-fade-in 0.4s ease-out;
}

/* ── Chronicle Header ───────────────────────────────────────────── */

.chronicle-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding-top: 8px;
}

.header-frame {
  position: relative;
  text-align: center;
  padding: 20px 40px;
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
.header-ornament.bottom { margin-top: 2px; }

.chronicle-title {
  font-family: 'Press Start 2P', var(--font-pixel), monospace;
  font-size: 16px;
  color: var(--pixel-primary);
  margin: 10px 0 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  text-shadow: 0 0 12px rgba(65, 166, 246, 0.3);
}

.title-icon {
  font-size: 20px;
  color: var(--pixel-info);
}

.chronicle-subtitle {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
  margin: 0 0 6px;
  letter-spacing: 3px;
}

.quest-new-btn {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  padding: 10px 24px;
  border: 3px solid var(--pixel-primary);
  background: transparent;
  color: var(--pixel-primary);
  cursor: pointer;
  box-shadow: 3px 3px 0 var(--pixel-shadow);
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.12s ease, color 0.12s ease;
}

.quest-new-btn:hover {
  background: var(--pixel-primary);
  color: var(--pixel-bg);
}

.btn-icon {
  font-size: 10px;
}

/* ── Journey Stats ───────────────────────────────────────────────── */

.journey-stats {
  display: flex;
  justify-content: flex-end;
}

.tab-count {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
}

.count-num {
  font-family: 'VT323', monospace;
  font-size: 16px;
  color: var(--pixel-info);
}

/* ── Loading ─────────────────────────────────────────────────────── */

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 80px 0;
}

.loading-text {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
  margin: 0;
}

/* ── Empty State ─────────────────────────────────────────────────── */

.empty-chronicle {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

.empty-scroll {
  width: 100%;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.scroll-top,
.scroll-bottom {
  width: 80%;
  height: 6px;
  background: var(--pixel-border);
  border: 2px solid var(--pixel-border);
  box-shadow: 3px 3px 0 var(--pixel-shadow);
}

.scroll-body {
  width: 100%;
  border-left: 2px solid var(--pixel-border);
  border-right: 2px solid var(--pixel-border);
  background: var(--pixel-bg-secondary);
  padding: 40px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
}

.empty-map {
  position: relative;
  width: 100px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.map-path-start {
  position: absolute;
  left: 10px;
  bottom: 0;
  width: 2px;
  height: 50px;
  background: repeating-linear-gradient(
    180deg,
    var(--pixel-border) 0px,
    var(--pixel-border) 4px,
    transparent 4px,
    transparent 8px
  );
  transform: rotate(-30deg);
}

.map-compass {
  font-size: 28px;
  color: var(--pixel-primary);
  opacity: 0.3;
  animation: marker-pulse 3s ease-in-out infinite;
}

.map-question {
  position: absolute;
  top: 8px;
  right: 12px;
  font-family: 'Press Start 2P', monospace;
  font-size: 18px;
  color: var(--pixel-warning);
  opacity: 0.6;
}

.empty-title {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 13px;
  font-weight: 700;
  color: var(--pixel-text);
  margin: 0;
}

.empty-desc {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
  margin: 0;
}

/* ── Journey Timeline ────────────────────────────────────────────── */

.journey-timeline {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 16px 0 0;
}

/* The central path line */
.timeline-path {
  position: absolute;
  left: 50%;
  top: 40px;
  bottom: 60px;
  width: 3px;
  transform: translateX(-50%);
  background: repeating-linear-gradient(
    180deg,
    var(--pixel-border) 0px,
    var(--pixel-border) 6px,
    transparent 6px,
    transparent 12px
  );
  opacity: 0.6;
  animation: path-flow 2s linear infinite;
}

.timeline-start-marker {
  display: flex;
  justify-content: center;
  margin-bottom: 8px;
}

.marker-diamond {
  font-size: 14px;
  color: var(--pixel-primary);
  opacity: 0.6;
}

/* ── Milestone Entry ─────────────────────────────────────────────── */

.milestone {
  position: relative;
  display: flex;
  align-items: flex-start;
  margin-bottom: 32px;
  animation: chronicle-fade-in 0.4s ease-out backwards;
}

.milestone-left {
  justify-content: flex-start;
  padding-right: calc(50% + 36px);
  animation-name: milestone-enter-left;
}

.milestone-right {
  justify-content: flex-end;
  padding-left: calc(50% + 36px);
  animation-name: milestone-enter-right;
}

/* Waypoint Node */
.waypoint-node {
  position: absolute;
  left: 50%;
  top: 16px;
  width: 28px;
  height: 28px;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
  z-index: 2;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.waypoint-icon {
  font-size: 12px;
  color: var(--pixel-text-secondary);
  transition: color 0.2s ease;
}

.waypoint-node.published {
  border-color: var(--pixel-primary);
  background: color-mix(in srgb, var(--pixel-primary) 15%, var(--pixel-bg));
}

.waypoint-node.published .waypoint-icon {
  color: var(--pixel-primary);
}

/* Connection line from node to card */
.connection-line {
  position: absolute;
  top: 29px;
  width: 36px;
  height: 2px;
  background: repeating-linear-gradient(
    90deg,
    var(--pixel-border) 0px,
    var(--pixel-border) 3px,
    transparent 3px,
    transparent 6px
  );
  opacity: 0.5;
}

.milestone-left .connection-line {
  right: calc(50% + 14px);
}

.milestone-right .connection-line {
  left: calc(50% + 14px);
}

/* ── Milestone Card ──────────────────────────────────────────────── */

.milestone-card {
  position: relative;
  flex: 1;
  background: var(--pixel-card-bg);
  cursor: pointer;
  overflow: hidden;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.milestone-card:hover {
  border-color: var(--pixel-primary);
}

.milestone-card:hover ~ .waypoint-node,
.milestone:hover .waypoint-node {
  border-color: var(--pixel-primary);
  box-shadow: 0 0 8px rgba(65, 166, 246, 0.3);
}

.card-corner-deco {
  position: absolute;
  bottom: 6px;
  right: 8px;
  font-size: 5px;
  color: var(--pixel-primary);
  opacity: 0.2;
}

/* Card Header Bar */
.card-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid var(--pixel-border);
  background: var(--pixel-bg-secondary);
}

.quest-status {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 9px;
  padding: 2px 8px;
  border: 1px solid;
}

.quest-status.published {
  color: var(--pixel-success);
  border-color: var(--pixel-success);
  background: rgba(56, 183, 100, 0.08);
}

.quest-status.draft {
  color: var(--pixel-text-secondary);
  border-color: var(--pixel-border);
  background: rgba(123, 143, 170, 0.08);
}

.quest-date {
  font-family: 'VT323', var(--font-pixel), monospace;
  font-size: 12px;
  color: var(--pixel-text-secondary);
}

/* Card Content */
.card-content {
  display: flex;
  gap: 12px;
  padding: 12px;
}

.card-cover-frame {
  position: relative;
  flex-shrink: 0;
  width: 80px;
  height: 60px;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
  overflow: hidden;
}

.cover-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  image-rendering: pixelated;
}

.cover-frame-corner {
  position: absolute;
  width: 6px;
  height: 6px;
  border-color: var(--pixel-primary);
  opacity: 0.4;
}
.cover-frame-corner.tl { top: 0; left: 0; border-top: 2px solid; border-left: 2px solid; }
.cover-frame-corner.tr { top: 0; right: 0; border-top: 2px solid; border-right: 2px solid; }
.cover-frame-corner.bl { bottom: 0; left: 0; border-bottom: 2px solid; border-left: 2px solid; }
.cover-frame-corner.br { bottom: 0; right: 0; border-bottom: 2px solid; border-right: 2px solid; }

.card-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.quest-title {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 13px;
  font-weight: 700;
  color: var(--pixel-text);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quest-summary {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 0;
}

.quest-attrs {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.attr-tag {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 8px;
  padding: 1px 6px;
  border: 1px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  background: var(--pixel-bg);
}

/* Card Footer */
.card-footer-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  border-top: 1px solid var(--pixel-border);
  background: var(--pixel-bg-secondary);
}

.chapter-num {
  font-family: 'VT323', monospace;
  font-size: 12px;
  color: var(--pixel-primary);
  opacity: 0.6;
  letter-spacing: 1px;
}

.card-actions {
  display: flex;
  gap: 2px;
}

.action-btn {
  background: none;
  border: 1px solid transparent;
  color: var(--pixel-text-secondary);
  cursor: pointer;
  font-size: 12px;
  padding: 2px 6px;
  transition: color 0.1s, border-color 0.1s;
}

.action-btn:hover {
  color: var(--pixel-primary);
  border-color: var(--pixel-primary);
}

.action-btn.danger:hover {
  color: var(--pixel-accent);
  border-color: var(--pixel-accent);
}

/* ── Timeline End ────────────────────────────────────────────────── */

.timeline-end-marker {
  display: flex;
  justify-content: center;
  padding-top: 16px;
  padding-bottom: 8px;
}

.path-continues {
  display: flex;
  align-items: center;
  gap: 10px;
  opacity: 0.4;
}

.continues-dots {
  display: flex;
  gap: 3px;
}

.continues-dots span {
  font-family: 'VT323', monospace;
  font-size: 14px;
  color: var(--pixel-text-secondary);
  line-height: 1;
}

.continues-text {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 10px;
  color: var(--pixel-text-secondary);
  letter-spacing: 2px;
}

/* ═══════════════════════════════════════════════
   Detail Modal
   ═══════════════════════════════════════════════ */

.detail-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 32px 16px;
  background: rgba(0, 0, 0, 0.7);
  overflow-y: auto;
}

.detail-modal {
  position: relative;
  width: 100%;
  max-width: 70%;
  background: var(--pixel-card-bg);
  margin: auto 0;
}

.modal-corner {
  position: absolute;
  font-size: 6px;
  color: var(--pixel-primary);
  opacity: 0.35;
  line-height: 1;
}
.modal-corner.tl { top: 6px; left: 8px; }
.modal-corner.tr { top: 6px; right: 8px; }
.modal-corner.bl { bottom: 6px; left: 8px; }
.modal-corner.br { bottom: 6px; right: 8px; }

.modal-top-bar {
  position: sticky;
  top: 0;
  z-index: 3;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 2px solid var(--pixel-border);
  background: var(--pixel-bg-secondary);
}

.modal-close-btn {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  padding: 4px 10px;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
  color: var(--pixel-text-secondary);
  cursor: pointer;
  transition: border-color 0.1s, color 0.1s;
}

.modal-close-btn:hover {
  border-color: var(--pixel-primary);
  color: var(--pixel-primary);
}

.modal-actions {
  display: flex;
  gap: 6px;
}

.modal-action-btn {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  padding: 4px 10px;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
  color: var(--pixel-text-secondary);
  cursor: pointer;
  transition: border-color 0.1s, color 0.1s;
}

.modal-action-btn:hover {
  border-color: var(--pixel-primary);
  color: var(--pixel-primary);
}

.modal-action-btn.danger:hover {
  border-color: var(--pixel-accent);
  color: var(--pixel-accent);
}

.modal-body {
  max-height: calc(90vh - 60px);
  overflow-y: auto;
}

.modal-cover {
  width: 100%;
  height: 200px;
  position: relative;
  overflow: hidden;
}

.modal-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.modal-cover-fade {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 80px;
  background: linear-gradient(to bottom, transparent, var(--pixel-card-bg));
  pointer-events: none;
}

.modal-header {
  padding: 0 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.modal-header.no-cover {
  padding-top: 20px;
}

.modal-meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-status {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 9px;
  padding: 2px 8px;
  border: 1px solid;
}

.modal-status.published {
  color: var(--pixel-success);
  border-color: var(--pixel-success);
  background: rgba(56, 183, 100, 0.08);
}

.modal-status.draft {
  color: var(--pixel-text-secondary);
  border-color: var(--pixel-border);
  background: rgba(123, 143, 170, 0.08);
}

.modal-date {
  font-family: 'VT323', var(--font-pixel), monospace;
  font-size: 12px;
  color: var(--pixel-text-secondary);
}

.modal-title {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 18px;
  font-weight: 700;
  color: var(--pixel-text);
  margin: 0;
  line-height: 1.4;
}

.modal-summary {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-text-secondary);
  line-height: 1.6;
  margin: 0;
}

.modal-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.modal-tag {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 9px;
  padding: 2px 8px;
  border: 2px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  background: var(--pixel-bg);
}

.modal-content {
  padding: 20px 24px 24px;
}

.modal-content :deep(.md-editor) {
  border: none !important;
  background-color: transparent !important;
  --md-bk-color: transparent !important;
  --md-color: var(--pixel-text) !important;
}

.modal-content :deep(.md-editor-preview) {
  --md-theme-color: var(--pixel-text) !important;
  --md-theme-color-reverse: var(--pixel-bg) !important;
  --md-theme-color-hover: var(--pixel-bg-secondary) !important;
  --md-theme-color-hover-inset: var(--pixel-border) !important;
  --md-theme-link-color: var(--pixel-primary) !important;
  --md-theme-link-hover-color: var(--pixel-info) !important;
  --md-theme-border-color: var(--pixel-border) !important;
  --md-theme-border-color-reverse: var(--pixel-text) !important;
  --md-theme-border-color-inset: var(--pixel-border) !important;
  --md-theme-bg-color: transparent !important;
  --md-theme-bg-color-inset: var(--pixel-bg-secondary) !important;
  --md-theme-code-inline-color: var(--pixel-primary) !important;
  --md-theme-code-inline-bg-color: rgba(65, 166, 246, 0.12) !important;
  --md-theme-code-inline-radius: 0 !important;
  --md-theme-code-block-color: var(--pixel-text) !important;
  --md-theme-code-block-bg-color: var(--pixel-bg) !important;
  --md-theme-code-before-bg-color: var(--pixel-bg) !important;
  --md-theme-code-block-radius: 0 !important;
  --md-theme-code-copy-tips-color: var(--pixel-text) !important;
  --md-theme-code-copy-tips-bg-color: var(--pixel-bg-secondary) !important;
  --md-theme-code-active-color: var(--pixel-primary) !important;
  --md-theme-radius-s: 0 !important;
  --md-theme-radius-m: 0 !important;
  --md-color: var(--pixel-text) !important;

  background: transparent !important;
  padding: 0 !important;
  font-family: var(--font-pixel), 'Ark Pixel', monospace !important;
  font-size: 13px !important;
  line-height: 1.85 !important;
  color: var(--pixel-text) !important;
  word-break: break-word;
}

.modal-content :deep(.md-editor-preview-wrapper) {
  padding: 0 !important;
  max-width: 100% !important;
}

.modal-content :deep(.md-editor-preview p) {
  margin: 0 0 14px !important;
  color: var(--pixel-text) !important;
}

.modal-content :deep(.md-editor-preview h1),
.modal-content :deep(.md-editor-preview h2),
.modal-content :deep(.md-editor-preview h3),
.modal-content :deep(.md-editor-preview h4),
.modal-content :deep(.md-editor-preview h5),
.modal-content :deep(.md-editor-preview h6) {
  font-family: var(--font-pixel), 'Ark Pixel', monospace !important;
  color: var(--pixel-text) !important;
  margin: 24px 0 10px !important;
  font-weight: 700 !important;
  line-height: 1.3 !important;
}

.modal-content :deep(.md-editor-preview h1) { font-size: 18px !important; }
.modal-content :deep(.md-editor-preview h2) { font-size: 16px !important; }
.modal-content :deep(.md-editor-preview h3) { font-size: 14px !important; }
.modal-content :deep(.md-editor-preview h4) { font-size: 13px !important; }
.modal-content :deep(.md-editor-preview h5) { font-size: 12px !important; }
.modal-content :deep(.md-editor-preview h6) { font-size: 11px !important; color: var(--pixel-text-secondary) !important; }

.modal-content :deep(.md-editor-preview a) {
  color: var(--pixel-primary) !important;
  text-decoration: none !important;
  border-bottom: 1px solid color-mix(in srgb, var(--pixel-primary) 40%, transparent) !important;
}

.modal-content :deep(.md-editor-preview code) {
  font-family: 'VT323', var(--font-pixel), monospace !important;
  font-size: 14px !important;
  color: var(--pixel-primary) !important;
  background: rgba(65, 166, 246, 0.12) !important;
  padding: 1px 5px !important;
  border: 1px solid var(--pixel-border) !important;
  border-radius: 0 !important;
}

.modal-content :deep(.md-editor-preview pre) {
  background: var(--pixel-bg) !important;
  border: 2px solid var(--pixel-border) !important;
  border-radius: 0 !important;
  padding: 14px !important;
  margin: 14px 0 !important;
}

.modal-content :deep(.md-editor-preview pre code) {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  font-size: 13px !important;
  color: var(--pixel-text) !important;
}

.modal-content :deep(.md-editor-preview blockquote) {
  margin: 14px 0 !important;
  padding: 10px 16px !important;
  background: var(--pixel-bg-secondary) !important;
  border-left: 3px solid var(--pixel-primary) !important;
  border-radius: 0 !important;
}

.modal-content :deep(.md-editor-preview blockquote p) {
  color: var(--pixel-text-secondary) !important;
}

.modal-content :deep(.md-editor-preview ul),
.modal-content :deep(.md-editor-preview ol) {
  margin: 10px 0 !important;
  padding-left: 22px !important;
}

.modal-content :deep(.md-editor-preview li) {
  margin: 4px 0 !important;
  line-height: 1.75 !important;
  color: var(--pixel-text) !important;
}

.modal-content :deep(.md-editor-preview table) {
  width: 100% !important;
  border-collapse: collapse !important;
  border: 2px solid var(--pixel-border) !important;
}

.modal-content :deep(.md-editor-preview th) {
  font-family: var(--font-pixel), 'Ark Pixel', monospace !important;
  font-size: 11px !important;
  color: var(--pixel-text) !important;
  background: var(--pixel-bg-secondary) !important;
  border: 1px solid var(--pixel-border) !important;
}

.modal-content :deep(.md-editor-preview td) {
  font-size: 12px !important;
  color: var(--pixel-text) !important;
  border: 1px solid var(--pixel-border) !important;
}

.modal-content :deep(.md-editor-preview hr) {
  border: none !important;
  height: 2px !important;
  background: var(--pixel-border) !important;
}

.modal-content :deep(.md-editor-preview img) {
  border: 2px solid var(--pixel-border) !important;
  max-width: 100% !important;
  display: block !important;
  margin: 14px auto !important;
}

/* Modal transition */
.modal-enter-active {
  animation: pixel-scale-in 0.2s ease-out;
}

.modal-leave-active {
  animation: pixel-scale-in 0.15s ease-in reverse;
}

/* ═══════════════════════════════════════════════
   Responsive — Single Column on Mobile
   ═══════════════════════════════════════════════ */

@media (max-width: 768px) {
  .chronicle-header {
    padding-top: 0;
  }

  .header-frame {
    padding: 16px 24px;
  }

  .chronicle-title {
    font-size: 12px;
  }

  .chronicle-subtitle {
    font-size: 10px;
    letter-spacing: 1px;
  }

  /* Timeline becomes left-aligned */
  .timeline-path {
    left: 20px;
  }

  .milestone-left,
  .milestone-right {
    padding-left: 52px;
    padding-right: 0;
    justify-content: flex-start;
    animation-name: milestone-enter-left;
  }

  .milestone-left .connection-line,
  .milestone-right .connection-line {
    left: 34px;
    right: auto;
    width: 18px;
  }

  .waypoint-node {
    left: 20px;
    width: 24px;
    height: 24px;
  }

  .waypoint-icon {
    font-size: 10px;
  }

  .card-content {
    flex-direction: column;
    gap: 8px;
  }

  .card-cover-frame {
    width: 100%;
    height: 80px;
  }
}

@media (max-width: 480px) {
  .chronicle-title {
    font-size: 11px;
    gap: 6px;
  }

  .title-icon {
    font-size: 16px;
  }

  .header-frame {
    padding: 14px 16px;
  }

  .milestone-left,
  .milestone-right {
    padding-left: 44px;
    margin-bottom: 24px;
  }

  .timeline-path {
    left: 16px;
  }

  .waypoint-node {
    left: 16px;
    width: 20px;
    height: 20px;
  }

  .milestone-left .connection-line,
  .milestone-right .connection-line {
    left: 26px;
    width: 18px;
  }
}
</style>
