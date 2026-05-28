<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'
import '../styles/blog-content.css'
import { getBlogByShareToken } from '../api/journals'
import type { Blog } from '../types/journal'

const route = useRoute()
const router = useRouter()

const blog = ref<Blog | null>(null)
const loading = ref(true)
const error = ref('')

async function loadBlog() {
  const token = route.params.token as string
  if (!token) { error.value = '无效链接'; loading.value = false; return }
  try {
    blog.value = await getBlogByShareToken(token)
  } catch {
    error.value = '博客不存在或链接已失效'
  } finally {
    loading.value = false
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric',
  })
}

onMounted(loadBlog)
</script>

<template>
  <div class="share-page">
    <div v-if="loading" class="loading-state"><div class="pixel-loading"></div></div>

    <div v-else-if="error" class="error-state">
      <div class="error-icon">◈</div>
      <div class="error-text">{{ error }}</div>
    </div>

    <template v-else-if="blog">
      <article class="share-article pixel-border">
        <div v-if="blog.cover_url" class="share-cover">
          <img :src="blog.cover_url" alt="" />
          <div class="cover-fade"></div>
        </div>

        <div class="share-header" :class="{ 'no-cover': !blog.cover_url }">
          <span class="share-date">{{ formatDate(blog.created_at) }}</span>
          <h1 class="share-title">{{ blog.title }}</h1>
          <p v-if="blog.summary" class="share-summary">{{ blog.summary }}</p>
          <div v-if="blog.tags.length" class="share-tags">
            <span v-for="tag in blog.tags" :key="tag" class="share-tag">{{ tag }}</span>
          </div>
        </div>

        <hr class="pixel-divider" style="margin: 0 24px;" />
        <div class="share-content blog-scroll-content">
          <MdPreview :model-value="blog.content || ''" />
        </div>
      </article>

      <div class="share-footer">
        <span class="footer-text">来自 <span class="footer-brand">PixelPack</span></span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.share-page {
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

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 80px 0;
}

.error-icon { font-size: 48px; color: var(--pixel-border); }
.error-text { font-family: var(--font-pixel), monospace; font-size: 12px; color: var(--pixel-text-secondary); }

.share-article {
  background: var(--pixel-card-bg);
  overflow: hidden;
}

.share-cover {
  width: 100%;
  height: 200px;
  position: relative;
  overflow: hidden;
}

.share-cover img {
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

.share-header {
  padding: 0 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.share-header.no-cover {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.share-date {
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

.share-title {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 20px;
  font-weight: 700;
  color: var(--pixel-text);
  margin: 0;
  line-height: 1.4;
}

.share-summary {
  font-size: 13px;
  color: var(--pixel-text-secondary);
  line-height: 1.6;
  margin: 0;
}

.share-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.share-tag {
  font-size: 9px;
  padding: 2px 8px;
  border: 2px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  background: var(--pixel-bg);
}

.share-content {
  /* styled by blog-content.css */
}

/* ── md-editor-v3 theme override via :deep() ─────────────────────── */

.share-content :deep(.md-editor) {
  border: none !important;
  background-color: transparent !important;
  --md-bk-color: transparent !important;
  --md-color: var(--pixel-text) !important;
}

.share-content :deep(.md-editor-preview) {
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

.share-content :deep(.md-editor-preview-wrapper) {
  padding: 0 !important;
  max-width: 100% !important;
}

.share-content :deep(.md-editor-preview p) {
  margin: 0 0 14px !important;
  color: var(--pixel-text) !important;
}

.share-content :deep(.md-editor-preview h1),
.share-content :deep(.md-editor-preview h2),
.share-content :deep(.md-editor-preview h3),
.share-content :deep(.md-editor-preview h4),
.share-content :deep(.md-editor-preview h5),
.share-content :deep(.md-editor-preview h6) {
  font-family: var(--font-pixel), 'Ark Pixel', monospace !important;
  color: var(--pixel-text) !important;
  margin: 24px 0 10px !important;
  font-weight: 700 !important;
  line-height: 1.3 !important;
}

.share-content :deep(.md-editor-preview h1) { font-size: 18px !important; }
.share-content :deep(.md-editor-preview h2) { font-size: 16px !important; }
.share-content :deep(.md-editor-preview h3) { font-size: 14px !important; }
.share-content :deep(.md-editor-preview h4) { font-size: 13px !important; }
.share-content :deep(.md-editor-preview h5) { font-size: 12px !important; }
.share-content :deep(.md-editor-preview h6) { font-size: 11px !important; color: var(--pixel-text-secondary) !important; }

.share-content :deep(.md-editor-preview a) {
  color: var(--pixel-primary) !important;
  text-decoration: none !important;
  border-bottom: 1px solid color-mix(in srgb, var(--pixel-primary) 40%, transparent) !important;
}

.share-content :deep(.md-editor-preview code) {
  font-family: 'VT323', var(--font-pixel), monospace !important;
  font-size: 14px !important;
  color: var(--pixel-primary) !important;
  background: rgba(65, 166, 246, 0.12) !important;
  padding: 1px 5px !important;
  border: 1px solid var(--pixel-border) !important;
  border-radius: 0 !important;
}

.share-content :deep(.md-editor-preview pre) {
  background: var(--pixel-bg) !important;
  border: 2px solid var(--pixel-border) !important;
  border-radius: 0 !important;
  padding: 14px !important;
  margin: 14px 0 !important;
}

.share-content :deep(.md-editor-preview pre code) {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  font-size: 13px !important;
  color: var(--pixel-text) !important;
}

.share-content :deep(.md-editor-preview blockquote) {
  margin: 14px 0 !important;
  padding: 10px 16px !important;
  background: var(--pixel-bg-secondary) !important;
  border-left: 3px solid var(--pixel-primary) !important;
  border-radius: 0 !important;
}

.share-content :deep(.md-editor-preview blockquote p) {
  color: var(--pixel-text-secondary) !important;
}

.share-content :deep(.md-editor-preview ul),
.share-content :deep(.md-editor-preview ol) {
  margin: 10px 0 !important;
  padding-left: 22px !important;
}

.share-content :deep(.md-editor-preview li) {
  margin: 4px 0 !important;
  line-height: 1.75 !important;
  color: var(--pixel-text) !important;
}

.share-content :deep(.md-editor-preview ul li::marker) {
  color: var(--pixel-text-secondary) !important;
  font-size: 10px;
}

.share-content :deep(.md-editor-preview ol li::marker) {
  color: var(--pixel-text-secondary) !important;
  font-family: 'VT323', monospace;
  font-size: 14px;
}

.share-content :deep(.md-editor-preview table) {
  width: 100% !important;
  border-collapse: collapse !important;
  border: 2px solid var(--pixel-border) !important;
}

.share-content :deep(.md-editor-preview th) {
  font-family: var(--font-pixel), 'Ark Pixel', monospace !important;
  font-size: 11px !important;
  color: var(--pixel-text) !important;
  background: var(--pixel-bg-secondary) !important;
  border: 1px solid var(--pixel-border) !important;
}

.share-content :deep(.md-editor-preview td) {
  font-size: 12px !important;
  color: var(--pixel-text) !important;
  border: 1px solid var(--pixel-border) !important;
}

.share-content :deep(.md-editor-preview hr) {
  border: none !important;
  height: 2px !important;
  background: var(--pixel-border) !important;
}

.share-content :deep(.md-editor-preview img) {
  border: 2px solid var(--pixel-border) !important;
  max-width: 100% !important;
  display: block !important;
  margin: 14px auto !important;
}

.share-content :deep(.md-editor-preview strong) {
  color: var(--pixel-text) !important;
}

.share-content :deep(.md-editor-preview del) {
  color: var(--pixel-text-secondary) !important;
  opacity: 0.6;
}

.share-content :deep(.md-editor-preview mark) {
  background: color-mix(in srgb, var(--pixel-warning) 25%, transparent) !important;
  color: var(--pixel-text) !important;
}

.share-footer {
  display: flex;
  justify-content: center;
  padding: 16px 0 32px;
}

.footer-text {
  font-family: var(--font-pixel), monospace;
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

.footer-brand {
  color: var(--pixel-primary);
  font-weight: 700;
}

@keyframes pixel-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
