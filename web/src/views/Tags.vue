<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { listTags, createTag, updateTag, deleteTag } from '../api/metadata'
import type { Tag } from '../types/item'
import { useNotifyStore } from '../stores/notification'

const notify = useNotifyStore()

const loading = ref(true)
const error = ref<string | null>(null)
const tags = ref<Tag[]>([])

// New tag form
const showNewForm = ref(false)
const newForm = reactive({ name: '', color: '#41a6f6' })
const saving = ref(false)

// Inline edit
const editingId = ref<number | null>(null)
const editForm = reactive({ name: '', color: '' })

async function loadTags() {
  loading.value = true
  error.value = null
  try {
    tags.value = await listTags()
  } catch (e: any) {
    error.value = e?.message || '加载标签失败'
  } finally {
    loading.value = false
  }
}

function openNewForm() {
  showNewForm.value = true
  newForm.name = ''
  newForm.color = '#41a6f6'
}

function cancelNew() {
  showNewForm.value = false
}

async function handleCreate() {
  if (!newForm.name.trim()) return
  saving.value = true
  try {
    const tag = await createTag({ name: newForm.name.trim(), color: newForm.color })
    tags.value.push(tag)
    showNewForm.value = false
    newForm.name = ''
    newForm.color = '#41a6f6'
    notify.success('标签已创建')
  } catch (e: any) {
    error.value = e?.message || '创建标签失败'
  } finally {
    saving.value = false
  }
}

function startEdit(tag: Tag) {
  editingId.value = tag.id
  editForm.name = tag.name
  editForm.color = tag.color
}

function cancelEdit() {
  editingId.value = null
}

async function handleSaveEdit(id: number) {
  if (!editForm.name.trim()) return
  saving.value = true
  try {
    const updated = await updateTag(id, { name: editForm.name.trim(), color: editForm.color })
    const idx = tags.value.findIndex(t => t.id === id)
    if (idx !== -1) tags.value[idx] = updated
    editingId.value = null
    notify.success('标签已更新')
  } catch (e: any) {
    error.value = e?.message || '更新标签失败'
  } finally {
    saving.value = false
  }
}

async function handleDelete(tag: Tag) {
  if (!window.confirm(`确定要删除标签「${tag.name}」吗？`)) return
  try {
    await deleteTag(tag.id)
    tags.value = tags.value.filter(t => t.id !== tag.id)
    notify.success('标签已删除')
  } catch (e: any) {
    error.value = e?.message || '删除标签失败'
  }
}

onMounted(loadTags)
</script>

<template>
  <div class="tags-page animate-fade-in">
    <!-- Header -->
    <div class="page-header">
      <h1 class="page-title">◎ 标签管理</h1>
      <button class="pixel-btn primary pixel-btn-glow" @click="openNewForm" :disabled="showNewForm">
        + 新增标签
      </button>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="error-banner">
      <span class="error-icon">!</span>
      <span>{{ error }}</span>
      <button class="error-dismiss" @click="error = null">✕</button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="pixel-loading"></div>
      <span class="loading-text">加载中...</span>
    </div>

    <template v-else>
      <!-- New tag form -->
      <div v-if="showNewForm" class="form-card pixel-border animate-fade-in">
        <div class="form-header">
          <h3 class="form-title">+ 新增标签</h3>
        </div>
        <div class="form-body">
          <div class="form-row">
            <div class="form-field">
              <label class="form-label">名称 *</label>
              <input
                v-model="newForm.name"
                type="text"
                class="pixel-input"
                placeholder="标签名称"
                maxlength="30"
                @keydown.enter="handleCreate"
              />
            </div>
            <div class="form-field field-color">
              <label class="form-label">颜色</label>
              <div class="color-picker-wrap">
                <input v-model="newForm.color" type="color" class="color-input" />
                <span class="color-value">{{ newForm.color }}</span>
              </div>
            </div>
          </div>
          <div class="form-actions">
            <button
              class="pixel-btn success pixel-btn-glow"
              @click="handleCreate"
              :disabled="!newForm.name.trim() || saving"
            >
              {{ saving ? '...' : '保存' }}
            </button>
            <button class="pixel-btn" @click="cancelNew">取消</button>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="tags.length === 0 && !showNewForm" class="empty-state animate-fade-in">
        <div class="empty-icon">◎</div>
        <div class="empty-text">还没有标签</div>
        <button class="pixel-btn primary pixel-btn-glow" @click="openNewForm">
          + 创建第一个标签
        </button>
      </div>

      <!-- Tag grid -->
      <div v-if="tags.length > 0" class="tag-grid stagger-list">
        <div
          v-for="tag in tags"
          :key="tag.id"
          class="tag-card"
          :class="{ editing: editingId === tag.id }"
        >
          <!-- Display mode -->
          <template v-if="editingId !== tag.id">
            <div class="card-color-bar" :style="{ background: tag.color }"></div>
            <div class="card-body">
              <div class="card-top">
                <span class="color-dot" :style="{ background: tag.color }"></span>
                <span class="tag-name">{{ tag.name }}</span>
              </div>
              <span class="color-hex">{{ tag.color }}</span>
            </div>
            <div class="card-actions">
              <button class="card-action-btn" @click="startEdit(tag)" title="编辑">✎</button>
              <button class="card-action-btn danger" @click="handleDelete(tag)" title="删除">✕</button>
            </div>
          </template>

          <!-- Edit mode -->
          <template v-else>
            <div class="form-card inline-edit animate-fade-in">
              <div class="form-header">
                <h3 class="form-title">✎ 编辑标签</h3>
                <button class="close-btn" @click="cancelEdit">✕</button>
              </div>
              <div class="form-body">
                <div class="form-row">
                  <div class="form-field">
                    <label class="form-label">名称 *</label>
                    <input
                      v-model="editForm.name"
                      type="text"
                      class="pixel-input"
                      placeholder="标签名称"
                      maxlength="30"
                      @keydown.enter="handleSaveEdit(tag.id)"
                      @keydown.escape="cancelEdit"
                    />
                  </div>
                  <div class="form-field field-color">
                    <label class="form-label">颜色</label>
                    <input v-model="editForm.color" type="color" class="color-input" />
                  </div>
                </div>
                <div class="form-actions">
                  <button
                    class="pixel-btn success pixel-btn-glow"
                    @click="handleSaveEdit(tag.id)"
                    :disabled="!editForm.name.trim() || saving"
                  >
                    {{ saving ? '...' : '保存' }}
                  </button>
                  <button class="pixel-btn" @click="cancelEdit">CANCEL</button>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.tags-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ===== Header ===== */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.page-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 16px;
  color: var(--pixel-primary);
  margin: 0;
}

/* ===== Shared Buttons ===== */
.pixel-btn {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  padding: 8px 16px;
  border: 3px solid var(--pixel-border);
  background: var(--pixel-card-bg);
  color: var(--pixel-text);
  cursor: pointer;
  box-shadow: 3px 3px 0 var(--pixel-shadow);
  transition: transform 0.08s ease, box-shadow 0.15s ease, background 0.15s ease, color 0.15s ease;
  white-space: nowrap;
}

.pixel-btn:hover {
  border-color: var(--pixel-text-secondary);
}

.pixel-btn:active:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

.pixel-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pixel-btn.primary {
  background: var(--pixel-primary);
  border-color: var(--pixel-primary);
  color: #0e1225;
}

.pixel-btn.primary:hover {
  border-color: var(--pixel-text);
}

.pixel-btn.success {
  background: var(--pixel-success);
  border-color: var(--pixel-success);
  color: #0e1225;
}

.pixel-btn.success:hover {
  border-color: var(--pixel-text);
}

/* ===== Error ===== */
.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-accent);
  color: var(--pixel-accent);
  font-size: 13px;
}

.error-icon {
  font-family: 'Press Start 2P', monospace;
  font-size: 12px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--pixel-accent);
  color: var(--pixel-text);
  flex-shrink: 0;
}

.error-dismiss {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--pixel-accent);
  font-size: 16px;
  cursor: pointer;
  padding: 4px;
}

.error-dismiss:hover {
  color: var(--pixel-text);
}

/* ===== Loading ===== */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 16px;
}

.loading-text {
  font-family: 'Press Start 2P', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
}

/* ===== Pixel Input ===== */
.pixel-input {
  font-family: var(--font-pixel), 'Ark Pixel', 'Press Start 2P', monospace;
  font-size: 13px;
  padding: 8px 12px;
  background: var(--pixel-bg);
  border: 3px solid var(--pixel-border);
  color: var(--pixel-text);
  outline: none;
  width: 100%;
  box-sizing: border-box;
  transition: border-color 0.15s ease, box-shadow 0.25s ease;
}

.pixel-input::placeholder {
  color: var(--pixel-text-secondary);
  opacity: 0.6;
}

.pixel-input:focus {
  border-color: var(--pixel-primary);
  box-shadow: 0 0 0 1px var(--pixel-primary), 0 0 8px rgba(65, 166, 246, 0.15);
}

/* ===== Form Card (shared for new/edit) ===== */
.form-card {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  box-shadow: 3px 3px 0 var(--pixel-shadow);
}

.form-card.inline-edit {
  border-color: var(--pixel-primary);
  grid-column: 1 / -1;
}

.form-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 2px solid var(--pixel-border);
  background: var(--pixel-bg-secondary);
}

.form-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  color: var(--pixel-primary);
  margin: 0;
}

.close-btn {
  font-family: 'Press Start 2P', monospace;
  font-size: 12px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
  color: var(--pixel-text-secondary);
  cursor: pointer;
  padding: 0;
}

.close-btn:hover {
  border-color: var(--pixel-accent);
  color: var(--pixel-accent);
}

.form-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.field-color {
  flex: 0 0 150px;
}

.form-label {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  color: var(--pixel-text-secondary);
  letter-spacing: 0.5px;
}

.color-picker-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.color-input {
  width: 44px;
  height: 36px;
  padding: 2px;
  background: var(--pixel-bg);
  border: 3px solid var(--pixel-border);
  cursor: pointer;
}

.color-input::-webkit-color-swatch-wrapper {
  padding: 2px;
}

.color-input::-webkit-color-swatch {
  border: none;
}

.color-value {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  color: var(--pixel-text-secondary);
}

.form-actions {
  display: flex;
  gap: 8px;
  padding-top: 4px;
}

/* ===== Tag Grid ===== */
.tag-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.tag-card {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  box-shadow: 3px 3px 0 var(--pixel-shadow);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
  will-change: transform;
}

.tag-card:hover {
  border-color: var(--pixel-primary);
  box-shadow: 4px 6px 0 var(--pixel-shadow);
}

.tag-card:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

.tag-card.editing {
  grid-column: 1 / -1;
  border-color: var(--pixel-primary);
}

/* Color bar at top of card */
.card-color-bar {
  height: 6px;
  width: 100%;
  flex-shrink: 0;
}

.card-body {
  padding: 14px 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.color-dot {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  border: 2px solid var(--pixel-border);
}

.tag-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 14px;
  font-weight: 700;
  color: var(--pixel-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.color-hex {
  font-family: 'Press Start 2P', monospace;
  font-size: 7px;
  color: var(--pixel-text-secondary);
  letter-spacing: 0.5px;
  padding-left: 24px;
}

/* Card bottom actions */
.card-actions {
  display: flex;
  border-top: 2px solid var(--pixel-border);
}

.card-action-btn {
  flex: 1;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--pixel-bg);
  color: var(--pixel-text-secondary);
  cursor: pointer;
  font-size: 14px;
  padding: 0;
  border: none;
  border-right: 2px solid var(--pixel-border);
  transition: color 0.1s ease, background 0.1s ease;
}

.card-action-btn:last-child {
  border-right: none;
}

.card-action-btn:hover {
  color: var(--pixel-primary);
  background: var(--pixel-bg-secondary);
}

.card-action-btn.danger:hover {
  color: var(--pixel-accent);
}

.card-action-btn:active {
  background: var(--pixel-card-bg);
}

/* ===== Empty State ===== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  min-height: 350px;
}

.empty-icon {
  font-size: 64px;
  color: var(--pixel-border);
  line-height: 1;
  animation: pixel-float 3s ease-in-out infinite;
}

.empty-text {
  font-family: 'Press Start 2P', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
}

/* ===== Responsive ===== */
@media (max-width: 1024px) {
  .tag-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .tag-grid {
    grid-template-columns: 1fr;
  }

  .form-row {
    flex-direction: column;
    align-items: stretch;
  }

  .field-color {
    flex: 1;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
