<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { MdEditor, MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { createBlog, updateBlog, listBlogs } from '../api/journals'
import type { Blog } from '../types/journal'
import { useNotifyStore } from '../stores/notification'

const router = useRouter()
const route = useRoute()
const notify = useNotifyStore()

const isEdit = computed(() => !!route.params.id)
const blogId = computed(() => Number(route.params.id) || 0)

const title = ref('')
const content = ref('')
const summary = ref('')
const coverUrl = ref('')
const tagsInput = ref('')
const status = ref<'draft' | 'published'>('draft')
const loading = ref(false)
const saving = ref(false)

const coverFileInput = ref<HTMLInputElement | null>(null)

async function loadBlog() {
  if (!isEdit.value) return
  loading.value = true
  try {
    const blogs = await listBlogs()
    const blog = blogs.find((b: Blog) => b.id === blogId.value)
    if (!blog) { notify.error('博客不存在'); router.push('/blog'); return }
    title.value = blog.title
    content.value = blog.content || ''
    summary.value = blog.summary || ''
    coverUrl.value = blog.cover_url || ''
    tagsInput.value = blog.tags.join(', ')
    status.value = blog.status
  } catch {
    notify.error('加载失败')
  } finally {
    loading.value = false
  }
}

function triggerCoverUpload() {
  coverFileInput.value?.click()
}

async function handleCoverUpload(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files?.length) return
  const file = target.files[0]
  if (!file.type.startsWith('image/')) return
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch('/api/journals/blog/upload', {
      method: 'POST',
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      body: formData,
    })
    const data = await res.json()
    coverUrl.value = data.url
  } catch {
    notify.error('上传失败')
  }
}

async function handleSave(publishStatus: 'draft' | 'published') {
  if (!title.value.trim()) { notify.error('请输入标题'); return }
  saving.value = true
  const tags = tagsInput.value.split(/[,，]/).map(t => t.trim()).filter(Boolean)
  const payload = {
    title: title.value.trim(),
    content: content.value,
    summary: summary.value || undefined,
    cover_url: coverUrl.value || undefined,
    tags,
    status: publishStatus,
  }
  try {
    if (isEdit.value) {
      await updateBlog(blogId.value, payload)
      notify.success('已保存')
    } else {
      await createBlog(payload)
      notify.success(publishStatus === 'published' ? '已发布' : '已保存草稿')
    }
    router.push('/blog')
  } catch {
    notify.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadBlog)
</script>

<template>
  <div class="editor-page">
    <div v-if="loading" class="loading-state"><div class="pixel-loading"></div></div>

    <div v-else class="editor-layout">
      <div class="editor-top-bar">
        <button class="back-btn" @click="router.push('/blog')">◀ 返回</button>
        <div class="editor-actions">
          <button class="save-btn draft" :disabled="saving" @click="handleSave('draft')">
            {{ saving ? '...' : '保存草稿' }}
          </button>
          <button class="save-btn publish" :disabled="saving" @click="handleSave('published')">
            {{ saving ? '...' : '发布' }}
          </button>
        </div>
      </div>

      <div class="meta-section pixel-border">
        <input v-model="title" type="text" class="meta-title" placeholder="博客标题..." maxlength="200" />

        <div class="meta-row">
          <div class="meta-field">
            <label class="meta-label">封面</label>
            <div class="cover-upload" @click="triggerCoverUpload">
              <img v-if="coverUrl" :src="coverUrl" alt="Cover" class="cover-preview" />
              <span v-else class="cover-placeholder">+ 上传封面</span>
            </div>
            <input ref="coverFileInput" type="file" accept="image/*" class="hidden-input" @change="handleCoverUpload" />
          </div>
          <div class="meta-fields-col">
            <div class="meta-field">
              <label class="meta-label">摘要</label>
              <textarea v-model="summary" class="meta-textarea" placeholder="简短描述..." rows="2" maxlength="500"></textarea>
            </div>
            <div class="meta-field">
              <label class="meta-label">标签 (逗号分隔)</label>
              <input v-model="tagsInput" type="text" class="meta-input" placeholder="旅行, 技术, 生活..." />
            </div>
          </div>
        </div>
      </div>

      <div class="editor-section">
        <MdEditor v-model="content" language="zh-CN" :toolbarsExclude="['github']" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.editor-page {
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

.editor-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.editor-top-bar {
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

.editor-actions {
  display: flex;
  gap: 8px;
}

.save-btn {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  padding: 8px 16px;
  border: 3px solid var(--pixel-border);
  cursor: pointer;
  box-shadow: 3px 3px 0 var(--pixel-shadow);
}

.save-btn.draft {
  background: var(--pixel-bg);
  color: var(--pixel-text);
}

.save-btn.publish {
  background: var(--pixel-primary);
  border-color: var(--pixel-primary);
  color: var(--pixel-bg);
}

.save-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Meta section */
.meta-section {
  background: var(--pixel-card-bg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.meta-title {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 18px;
  font-weight: 700;
  color: var(--pixel-text);
  background: var(--pixel-bg);
  border: 3px solid var(--pixel-border);
  padding: 10px 12px;
  outline: none;
  width: 100%;
  box-sizing: border-box;
}

.meta-title:focus {
  border-color: var(--pixel-primary);
  box-shadow: 0 0 0 1px var(--pixel-primary);
}

.meta-title::placeholder { color: var(--pixel-text-secondary); opacity: 0.5; }

.meta-row {
  display: flex;
  gap: 16px;
}

.meta-fields-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.meta-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  color: var(--pixel-text-secondary);
}

.meta-input, .meta-textarea {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-text);
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  padding: 8px;
  outline: none;
  width: 100%;
  box-sizing: border-box;
}

.meta-textarea { resize: none; }

.meta-input:focus, .meta-textarea:focus {
  border-color: var(--pixel-primary);
}

.meta-input::placeholder, .meta-textarea::placeholder { color: var(--pixel-text-secondary); opacity: 0.5; }

.cover-upload {
  width: 200px;
  height: 112px;
  border: 2px dashed var(--pixel-border);
  background: var(--pixel-bg);
  cursor: pointer;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.12s;
}

.cover-upload:hover { border-color: var(--pixel-primary); }

.cover-preview { width: 100%; height: 100%; object-fit: cover; }

.cover-placeholder {
  font-family: var(--font-pixel), monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
}

.hidden-input { display: none; }

.editor-section {
  border: 3px solid var(--pixel-border);
}

@keyframes pixel-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
