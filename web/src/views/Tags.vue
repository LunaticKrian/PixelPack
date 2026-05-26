<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { listTags, createTag, updateTag, deleteTag } from '../api/metadata'
import type { Tag } from '../types/item'

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
  } catch (e: any) {
    error.value = e?.message || '删除标签失败'
  }
}

function colorAtOpacity(hex: string, opacity: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${opacity})`
}

onMounted(loadTags)
</script>

<template>
  <div class="tags-page animate-fade-in">
    <!-- Header -->
    <div class="page-header">
      <h1 class="page-title">◎ 标签管理</h1>
      <button class="btn btn-primary pixel-shadow" @click="openNewForm" :disabled="showNewForm">
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
      <span class="loading-text">LOADING...</span>
    </div>

    <template v-else>
      <!-- New tag form -->
      <div v-if="showNewForm" class="new-form pixel-border animate-fade-in">
        <div class="form-title">+ NEW TAG</div>
        <div class="form-row">
          <input
            v-model="newForm.name"
            type="text"
            class="pixel-input"
            placeholder="标签名称"
            maxlength="30"
            @keydown.enter="handleCreate"
          />
          <div class="color-picker-wrap">
            <input v-model="newForm.color" type="color" class="color-input" />
            <span class="color-label">COLOR</span>
          </div>
        </div>
        <div class="form-actions">
          <button
            class="btn btn-success pixel-shadow animate-press"
            @click="handleCreate"
            :disabled="!newForm.name.trim() || saving"
          >
            {{ saving ? '...' : 'SAVE' }}
          </button>
          <button class="btn btn-cancel pixel-shadow animate-press" @click="cancelNew">
            CANCEL
          </button>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="tags.length === 0 && !showNewForm" class="empty-state animate-fade-in">
        <div class="empty-icon">◎</div>
        <div class="empty-text">还没有标签</div>
        <button class="btn btn-primary pixel-shadow animate-press" @click="openNewForm">
          + 创建第一个标签
        </button>
      </div>

      <!-- Tag cloud -->
      <div v-if="tags.length > 0" class="tag-cloud">
        <div
          v-for="tag in tags"
          :key="tag.id"
          class="tag-badge"
          :class="{ editing: editingId === tag.id }"
          :style="{
            borderLeftColor: tag.color,
            background: colorAtOpacity(tag.color, 0.15),
          }"
        >
          <!-- Display mode -->
          <template v-if="editingId !== tag.id">
            <span class="tag-color-dot" :style="{ background: tag.color }"></span>
            <span class="tag-name">{{ tag.name }}</span>
            <div class="tag-actions">
              <button class="tag-btn tag-edit" @click="startEdit(tag)" title="编辑">✎</button>
              <button class="tag-btn tag-delete" @click="handleDelete(tag)" title="删除">✕</button>
            </div>
          </template>

          <!-- Edit mode -->
          <template v-else>
            <div class="edit-form-inline">
              <div class="form-row compact">
                <input
                  v-model="editForm.name"
                  type="text"
                  class="pixel-input"
                  placeholder="标签名称"
                  maxlength="30"
                  @keydown.enter="handleSaveEdit(tag.id)"
                  @keydown.escape="cancelEdit"
                />
                <input v-model="editForm.color" type="color" class="color-input" />
              </div>
              <div class="form-actions compact">
                <button
                  class="btn btn-success btn-sm pixel-shadow animate-press"
                  @click="handleSaveEdit(tag.id)"
                  :disabled="!editForm.name.trim() || saving"
                >
                  {{ saving ? '...' : 'SAVE' }}
                </button>
                <button class="btn btn-cancel btn-sm pixel-shadow animate-press" @click="cancelEdit">
                  CANCEL
                </button>
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
  font-weight: bold;
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

/* ===== Buttons ===== */
.btn {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  padding: 10px 16px;
  border: 3px solid;
  cursor: pointer;
  background: var(--pixel-card-bg);
  color: var(--pixel-text);
  transition: transform 0.05s steps(2);
  letter-spacing: 0.5px;
}

.btn:active:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  font-size: 8px;
  padding: 6px 10px;
}

.btn-primary {
  border-color: var(--pixel-primary);
  color: var(--pixel-primary);
}

.btn-primary:hover:not(:disabled) {
  background: var(--pixel-primary);
  color: var(--pixel-bg);
}

.btn-success {
  border-color: var(--pixel-success);
  color: var(--pixel-success);
}

.btn-success:hover:not(:disabled) {
  background: var(--pixel-success);
  color: var(--pixel-bg);
}

.btn-cancel {
  border-color: var(--pixel-border);
  color: var(--pixel-text-secondary);
}

.btn-cancel:hover:not(:disabled) {
  border-color: var(--pixel-text-secondary);
  color: var(--pixel-text);
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
  border-radius: 0;
  width: 100%;
  box-sizing: border-box;
}

.pixel-input::placeholder {
  color: var(--pixel-text-secondary);
  opacity: 0.6;
}

.pixel-input:focus {
  border-color: var(--pixel-primary);
}

/* ===== New Tag Form ===== */
.new-form {
  background: var(--pixel-card-bg);
  padding: 16px;
}

.form-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  color: var(--pixel-text-secondary);
  margin-bottom: 12px;
  letter-spacing: 1px;
}

.form-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.form-row.compact {
  gap: 8px;
}

.color-picker-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.color-label {
  font-family: 'Press Start 2P', monospace;
  font-size: 7px;
  color: var(--pixel-text-secondary);
  letter-spacing: 1px;
}

.color-input {
  width: 40px;
  height: 36px;
  padding: 2px;
  background: var(--pixel-bg);
  border: 3px solid var(--pixel-border);
  cursor: pointer;
  border-radius: 0;
}

.color-input::-webkit-color-swatch-wrapper {
  padding: 2px;
}

.color-input::-webkit-color-swatch {
  border: none;
  border-radius: 0;
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.form-actions.compact {
  margin-top: 8px;
}

/* ===== Tag Cloud ===== */
.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-start;
}

/* ===== Tag Badge ===== */
.tag-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 2px solid var(--pixel-border);
  border-left: 4px solid;
  border-radius: 0;
  font-size: 12px;
  transition: border-color 0.1s steps(2), box-shadow 0.1s steps(2);
  min-width: 120px;
  position: relative;
}

.tag-badge:hover {
  border-color: var(--pixel-text-secondary);
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.3);
}

.tag-badge:hover .tag-actions {
  opacity: 1;
  transform: translateX(0);
}

.tag-badge.editing {
  border-color: var(--pixel-primary);
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.3);
  padding: 10px 14px;
}

.tag-color-dot {
  width: 10px;
  height: 10px;
  flex-shrink: 0;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.tag-name {
  color: var(--pixel-text);
  font-family: var(--font-pixel), 'Ark Pixel', 'Press Start 2P', monospace;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 160px;
}

/* ===== Tag Actions ===== */
.tag-actions {
  display: flex;
  gap: 4px;
  margin-left: auto;
  opacity: 0;
  transform: translateX(4px);
  transition: opacity 0.15s steps(3), transform 0.15s steps(3);
}

.tag-btn {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  cursor: pointer;
  font-size: 11px;
  padding: 0;
  border-radius: 0;
  transition: border-color 0.1s steps(2), color 0.1s steps(2);
}

.tag-btn:hover {
  border-color: var(--pixel-text-secondary);
}

.tag-edit:hover {
  color: var(--pixel-primary);
  border-color: var(--pixel-primary);
}

.tag-delete:hover {
  color: var(--pixel-accent);
  border-color: var(--pixel-accent);
}

.tag-btn:active {
  transform: translate(1px, 1px);
}

/* ===== Inline Edit Form ===== */
.edit-form-inline {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
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
}

.empty-text {
  font-family: 'Press Start 2P', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
}

/* ===== Responsive ===== */
@media (max-width: 640px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .form-row {
    flex-direction: column;
    align-items: stretch;
  }

  .color-picker-wrap {
    flex-direction: row;
    gap: 8px;
  }

  .tag-badge {
    min-width: unset;
    width: 100%;
  }

  .tag-actions {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
