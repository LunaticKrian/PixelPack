<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'
import '../styles/blog-content.css'
import { listBlogs, deleteBlog } from '../api/journals'
import type { Blog } from '../types/journal'
import { useNotifyStore } from '../stores/notification'

const router = useRouter()
const route = useRoute()
const notify = useNotifyStore()

const blog = ref<Blog | null>(null)
const loading = ref(true)
const blogId = Number(route.params.id)

async function loadBlog() {
  loading.value = true
  try {
    const blogs = await listBlogs()
    const found = blogs.find((b: Blog) => b.id === blogId)
    if (!found) { notify.error('博客不存在'); router.push('/blog'); return }
    blog.value = found
  } catch {
    notify.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function handleDelete() {
  if (!blog.value) return
  try {
    await deleteBlog(blog.value.id)
    notify.success('已删除')
    router.push('/blog')
  } catch {
    notify.error('删除失败')
  }
}

function copyShareLink() {
  if (!blog.value?.share_token) return
  const url = `${window.location.origin}/share/${blog.value.share_token}`
  navigator.clipboard.writeText(url)
  notify.success('分享链接已复制')
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric',
  })
}

onMounted(loadBlog)
</script>

<template>
  <div class="detail-page">
    <div v-if="loading" class="loading-state"><div class="pixel-loading"></div></div>

    <template v-else-if="blog">
      <div class="detail-top-bar">
        <button class="back-btn" @click="router.push('/blog')">◀ 返回</button>
        <div class="detail-actions">
          <button v-if="blog.share_token" class="action-btn share" @click="copyShareLink">⎘ 分享</button>
          <button class="action-btn edit" @click="router.push(`/blog/${blog.id}/edit`)">✎ 编辑</button>
          <button class="action-btn danger" @click="handleDelete">✕ 删除</button>
        </div>
      </div>

      <article class="detail-article pixel-border">
        <div v-if="blog.cover_url" class="detail-cover">
          <img :src="blog.cover_url" alt="" />
          <div class="cover-fade"></div>
        </div>

        <div class="detail-header" :class="{ 'no-cover': !blog.cover_url }">
          <div class="detail-meta-row">
            <span class="detail-status" :class="blog.status">
              {{ blog.status === 'draft' ? '草稿' : '已发布' }}
            </span>
            <span class="detail-date">{{ formatDate(blog.created_at) }}</span>
          </div>
          <h1 class="detail-title">{{ blog.title }}</h1>
          <p v-if="blog.summary" class="detail-summary">{{ blog.summary }}</p>
          <div v-if="blog.tags.length" class="detail-tags">
            <span v-for="tag in blog.tags" :key="tag" class="detail-tag">{{ tag }}</span>
          </div>
        </div>

        <hr class="pixel-divider" style="margin: 0 24px;" />
        <div class="detail-content blog-scroll-content">
          <MdPreview :model-value="blog.content || ''" />
        </div>
      </article>
    </template>
  </div>
</template>

<style scoped>
.detail-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: pixel-fade-in 0.3s ease-out;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 60px;
}

.detail-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.back-btn {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  padding: 6px 12px;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
  color: var(--pixel-text-secondary);
  cursor: pointer;
}

.back-btn:hover { border-color: var(--pixel-primary); color: var(--pixel-primary); }

.detail-actions {
  display: flex;
  gap: 6px;
}

.action-btn {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  padding: 6px 12px;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
  color: var(--pixel-text-secondary);
  cursor: pointer;
  transition: border-color 0.1s, color 0.1s;
}

.action-btn:hover { border-color: var(--pixel-primary); color: var(--pixel-primary); }
.action-btn.danger:hover { border-color: var(--pixel-accent); color: var(--pixel-accent); }

.detail-article {
  background: var(--pixel-card-bg);
  overflow: hidden;
}

.detail-cover {
  width: 100%;
  height: 200px;
  position: relative;
  overflow: hidden;
}

.detail-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.cover-fade {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 100px;
  background: linear-gradient(to bottom, transparent, var(--pixel-card-bg));
  pointer-events: none;
}

.detail-header {
  padding: 0 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-header.no-cover {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-status {
  font-family: var(--font-pixel), monospace;
  font-size: 9px;
  padding: 2px 8px;
  border: 2px solid;
}

.detail-status.draft {
  color: var(--pixel-text-secondary);
  border-color: var(--pixel-text-secondary);
}

.detail-status.published {
  color: var(--pixel-success);
  border-color: var(--pixel-success);
}

.detail-date {
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

.detail-title {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 20px;
  font-weight: 700;
  color: var(--pixel-text);
  margin: 0;
  line-height: 1.4;
}

.detail-summary {
  font-size: 13px;
  color: var(--pixel-text-secondary);
  line-height: 1.6;
  margin: 0;
}

.detail-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.detail-tag {
  font-size: 9px;
  padding: 2px 8px;
  border: 2px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  background: var(--pixel-bg);
}

.detail-content {
  /* styled by blog-content.css */
}

/* ── md-editor-v3 theme override via :deep() ─────────────────────── */

.detail-content :deep(.md-editor) {
  border: none !important;
  background-color: transparent !important;
  --md-bk-color: transparent !important;
  --md-color: var(--pixel-text) !important;
}

.detail-content :deep(.md-editor-preview) {
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
  --md-theme-heading-color: var(--pixel-text) !important;
  --md-theme-heading-border: none !important;
  --md-theme-heading-1-border: 2px solid var(--pixel-border) !important;
  --md-theme-heading-2-border: 1px solid var(--pixel-border) !important;
  --md-theme-quote-color: var(--pixel-text-secondary) !important;
  --md-theme-quote-border: 3px solid var(--pixel-primary) !important;
  --md-theme-quote-bg-color: var(--pixel-bg-secondary) !important;
  --md-theme-table-stripe-color: color-mix(in srgb, var(--pixel-bg) 50%, transparent) !important;
  --md-theme-table-tr-bg-color: transparent !important;
  --md-theme-table-td-border-color: var(--pixel-border) !important;
  --md-color: var(--pixel-text) !important;

  background: transparent !important;
  padding: 0 !important;
  font-family: var(--font-pixel), 'Ark Pixel', monospace !important;
  font-size: 13px !important;
  line-height: 1.85 !important;
  color: var(--pixel-text) !important;
  word-break: break-word;
}

.detail-content :deep(.md-editor-preview-wrapper) {
  padding: 0 !important;
  max-width: 100% !important;
}

.detail-content :deep(.md-editor-preview p) {
  margin: 0 0 14px !important;
  color: var(--pixel-text) !important;
}

.detail-content :deep(.md-editor-preview h1),
.detail-content :deep(.md-editor-preview h2),
.detail-content :deep(.md-editor-preview h3),
.detail-content :deep(.md-editor-preview h4),
.detail-content :deep(.md-editor-preview h5),
.detail-content :deep(.md-editor-preview h6) {
  font-family: var(--font-pixel), 'Ark Pixel', monospace !important;
  color: var(--pixel-text) !important;
  margin: 24px 0 10px !important;
  font-weight: 700 !important;
  line-height: 1.3 !important;
}

.detail-content :deep(.md-editor-preview h1) { font-size: 18px !important; }
.detail-content :deep(.md-editor-preview h2) { font-size: 16px !important; }
.detail-content :deep(.md-editor-preview h3) { font-size: 14px !important; }
.detail-content :deep(.md-editor-preview h4) { font-size: 13px !important; }
.detail-content :deep(.md-editor-preview h5) { font-size: 12px !important; }
.detail-content :deep(.md-editor-preview h6) { font-size: 11px !important; color: var(--pixel-text-secondary) !important; }

.detail-content :deep(.md-editor-preview a) {
  color: var(--pixel-primary) !important;
  text-decoration: none !important;
  border-bottom: 1px solid color-mix(in srgb, var(--pixel-primary) 40%, transparent) !important;
}

.detail-content :deep(.md-editor-preview code) {
  font-family: 'VT323', var(--font-pixel), monospace !important;
  font-size: 14px !important;
  color: var(--pixel-primary) !important;
  background: rgba(65, 166, 246, 0.12) !important;
  padding: 1px 5px !important;
  border: 1px solid var(--pixel-border) !important;
  border-radius: 0 !important;
}

.detail-content :deep(.md-editor-preview pre) {
  background: var(--pixel-bg) !important;
  border: 2px solid var(--pixel-border) !important;
  border-radius: 0 !important;
  padding: 14px !important;
  margin: 14px 0 !important;
}

.detail-content :deep(.md-editor-preview pre code) {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  font-size: 13px !important;
  color: var(--pixel-text) !important;
}

.detail-content :deep(.md-editor-preview blockquote) {
  margin: 14px 0 !important;
  padding: 10px 16px !important;
  background: var(--pixel-bg-secondary) !important;
  border-left: 3px solid var(--pixel-primary) !important;
  border-radius: 0 !important;
}

.detail-content :deep(.md-editor-preview blockquote p) {
  color: var(--pixel-text-secondary) !important;
}

.detail-content :deep(.md-editor-preview ul),
.detail-content :deep(.md-editor-preview ol) {
  margin: 10px 0 !important;
  padding-left: 22px !important;
}

.detail-content :deep(.md-editor-preview li) {
  margin: 4px 0 !important;
  line-height: 1.75 !important;
  color: var(--pixel-text) !important;
}

.detail-content :deep(.md-editor-preview ul li::marker) {
  color: var(--pixel-text-secondary) !important;
  font-size: 10px;
}

.detail-content :deep(.md-editor-preview ol li::marker) {
  color: var(--pixel-text-secondary) !important;
  font-family: 'VT323', monospace;
  font-size: 14px;
}

.detail-content :deep(.md-editor-preview table) {
  width: 100% !important;
  border-collapse: collapse !important;
  border: 2px solid var(--pixel-border) !important;
}

.detail-content :deep(.md-editor-preview th) {
  font-family: var(--font-pixel), 'Ark Pixel', monospace !important;
  font-size: 11px !important;
  color: var(--pixel-text) !important;
  background: var(--pixel-bg-secondary) !important;
  border: 1px solid var(--pixel-border) !important;
}

.detail-content :deep(.md-editor-preview td) {
  font-size: 12px !important;
  color: var(--pixel-text) !important;
  border: 1px solid var(--pixel-border) !important;
}

.detail-content :deep(.md-editor-preview hr) {
  border: none !important;
  height: 2px !important;
  background: var(--pixel-border) !important;
}

.detail-content :deep(.md-editor-preview img) {
  border: 2px solid var(--pixel-border) !important;
  max-width: 100% !important;
  display: block !important;
  margin: 14px auto !important;
}

.detail-content :deep(.md-editor-preview strong) {
  color: var(--pixel-text) !important;
}

.detail-content :deep(.md-editor-preview del) {
  color: var(--pixel-text-secondary) !important;
  opacity: 0.6;
}

.detail-content :deep(.md-editor-preview mark) {
  background: color-mix(in srgb, var(--pixel-warning) 25%, transparent) !important;
  color: var(--pixel-text) !important;
}

@keyframes pixel-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
