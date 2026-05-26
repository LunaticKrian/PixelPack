<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { listCategories, createCategory, updateCategory, deleteCategory } from '../api/metadata'
import type { Category } from '../types/item'

interface CategoryForm {
  name: string
  icon: string
  color: string
  sort_order: number
  parent_id: number | null
}

const categories = ref<Category[]>([])
const loading = ref(true)
const error = ref('')

// Create form state
const showCreateForm = ref(false)
const createForm = ref<CategoryForm>({
  name: '',
  icon: '▦',
  color: '#41a6f6',
  sort_order: 0,
  parent_id: null,
})
const creating = ref(false)
const createError = ref('')

// Edit state
const editingId = ref<number | null>(null)
const editForm = ref<CategoryForm>({
  name: '',
  icon: '',
  color: '#41a6f6',
  sort_order: 0,
  parent_id: null,
})
const saving = ref(false)
const editError = ref('')

// Delete state
const deleteTarget = ref<Category | null>(null)
const deleting = ref(false)
const deleteError = ref('')

// Parent options: exclude currently editing category and its descendants
const parentOptions = computed(() => {
  const excludeId = editingId.value
  if (!excludeId) return categories.value
  return categories.value.filter(c => c.id !== excludeId)
})

function resetCreateForm() {
  createForm.value = {
    name: '',
    icon: '▦',
    color: '#41a6f6',
    sort_order: categories.value.length,
    parent_id: null,
  }
  createError.value = ''
}

function resetEditForm() {
  editingId.value = null
  editForm.value = { name: '', icon: '', color: '#41a6f6', sort_order: 0, parent_id: null }
  editError.value = ''
}

async function loadCategories() {
  loading.value = true
  error.value = ''
  try {
    categories.value = await listCategories()
  } catch (e: any) {
    error.value = '加载分类失败'
    console.error('Load categories error', e)
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!createForm.value.name.trim()) {
    createError.value = '分类名称不能为空'
    return
  }
  creating.value = true
  createError.value = ''
  try {
    const payload: any = {
      name: createForm.value.name.trim(),
      icon: createForm.value.icon || undefined,
      color: createForm.value.color || undefined,
      sort_order: createForm.value.sort_order || undefined,
      parent_id: createForm.value.parent_id || undefined,
    }
    const newCat = await createCategory(payload)
    categories.value.push(newCat)
    showCreateForm.value = false
    resetCreateForm()
  } catch (e: any) {
    createError.value = '创建失败，请重试'
    console.error('Create category error', e)
  } finally {
    creating.value = false
  }
}

function startEdit(cat: Category) {
  editingId.value = cat.id
  editForm.value = {
    name: cat.name,
    icon: cat.icon || '▦',
    color: cat.color || '#41a6f6',
    sort_order: cat.sort_order,
    parent_id: cat.parent_id,
  }
  editError.value = ''
}

async function handleSave() {
  if (!editForm.value.name.trim()) {
    editError.value = '分类名称不能为空'
    return
  }
  saving.value = true
  editError.value = ''
  try {
    const payload: any = {
      name: editForm.value.name.trim(),
      icon: editForm.value.icon || undefined,
      color: editForm.value.color || undefined,
      sort_order: editForm.value.sort_order || undefined,
      parent_id: editForm.value.parent_id || undefined,
    }
    const updated = await updateCategory(editingId.value!, payload)
    const idx = categories.value.findIndex(c => c.id === updated.id)
    if (idx !== -1) categories.value[idx] = updated
    resetEditForm()
  } catch (e: any) {
    editError.value = '保存失败，请重试'
    console.error('Update category error', e)
  } finally {
    saving.value = false
  }
}

function confirmDelete(cat: Category) {
  deleteTarget.value = cat
  deleteError.value = ''
}

async function handleDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await deleteCategory(deleteTarget.value.id)
    categories.value = categories.value.filter(c => c.id !== deleteTarget.value!.id)
    deleteTarget.value = null
  } catch (e: any) {
    if (e?.response?.status === 400) {
      deleteError.value = '该分类下存在物品，无法删除'
    } else {
      deleteError.value = '删除失败，请重试'
    }
    console.error('Delete category error', e)
  } finally {
    deleting.value = false
  }
}

function openCreate() {
  resetCreateForm()
  showCreateForm.value = true
}

onMounted(loadCategories)
</script>

<template>
  <div class="categories-page animate-fade-in">
    <!-- Header -->
    <div class="page-header">
      <h1 class="page-title">▦ 分类管理</h1>
      <button class="pixel-btn pixel-btn-glow primary" @click="openCreate" :disabled="loading">
        + 新增分类
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="pixel-loading"></div>
      <span class="loading-text">LOADING...</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-state">
      <div class="error-icon">!</div>
      <span class="error-text">{{ error }}</span>
      <button class="pixel-btn pixel-btn-glow" @click="loadCategories">重试</button>
    </div>

    <!-- Content -->
    <template v-else>
      <!-- Create Form (inline, expandable) -->
      <div v-if="showCreateForm" class="form-card animate-fade-in">
        <div class="form-header">
          <h3 class="form-title">+ 新增分类</h3>
          <button class="pixel-btn-close" @click="showCreateForm = false">✕</button>
        </div>
        <div class="form-body">
          <div class="form-grid">
            <div class="form-field">
              <label class="form-label">名称 *</label>
              <input
                v-model="createForm.name"
                type="text"
                class="pixel-input"
                placeholder="分类名称"
                maxlength="30"
                @keyup.enter="handleCreate"
              />
            </div>
            <div class="form-field">
              <label class="form-label">图标</label>
              <input
                v-model="createForm.icon"
                type="text"
                class="pixel-input icon-input"
                placeholder="▦"
                maxlength="4"
              />
            </div>
            <div class="form-field">
              <label class="form-label">颜色</label>
              <div class="color-picker-wrap">
                <input
                  v-model="createForm.color"
                  type="color"
                  class="pixel-color"
                />
                <span class="color-value">{{ createForm.color }}</span>
              </div>
            </div>
            <div class="form-field">
              <label class="form-label">排序</label>
              <input
                v-model.number="createForm.sort_order"
                type="number"
                class="pixel-input"
                min="0"
              />
            </div>
          </div>
          <div class="form-field">
            <label class="form-label">父分类</label>
            <select v-model="createForm.parent_id" class="pixel-select">
              <option :value="null">— 无 —</option>
              <option
                v-for="cat in categories"
                :key="cat.id"
                :value="cat.id"
              >{{ cat.icon || '▦' }} {{ cat.name }}</option>
            </select>
          </div>
          <div v-if="createError" class="form-error">{{ createError }}</div>
          <div class="form-actions">
            <button
              class="pixel-btn pixel-btn-glow success"
              @click="handleCreate"
              :disabled="creating"
            >
              {{ creating ? '保存中...' : '确认新增' }}
            </button>
            <button class="pixel-btn pixel-btn-glow" @click="showCreateForm = false">取消</button>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="categories.length === 0 && !showCreateForm" class="empty-state">
        <div class="empty-icon">▦</div>
        <div class="empty-text">还没有分类</div>
        <button class="pixel-btn pixel-btn-glow primary" @click="openCreate">+ 新增分类</button>
      </div>

      <!-- Category Grid -->
      <div v-else class="category-grid stagger-list">
        <div
          v-for="cat in categories"
          :key="cat.id"
          class="category-card pixel-card-hover"
          :class="{ editing: editingId === cat.id }"
        >
          <!-- Normal Card -->
          <template v-if="editingId !== cat.id">
            <div class="card-icon-area" :style="{ background: cat.color || '#182548' }">
              <span class="card-icon">{{ cat.icon || '▦' }}</span>
            </div>
            <div class="card-body">
              <div class="card-name">{{ cat.name }}</div>
              <div class="card-meta">
                <span v-if="cat.sort_order" class="card-sort">#{{ cat.sort_order }}</span>
                <span
                  v-if="cat.parent_id"
                  class="card-parent"
                >← {{ categories.find(c => c.id === cat.parent_id)?.name || '?' }}</span>
              </div>
            </div>
            <div class="card-color-bar" :style="{ background: cat.color || 'transparent' }"></div>
            <div class="card-actions">
              <button class="pixel-btn-sm" @click="startEdit(cat)" title="编辑">✎</button>
              <button class="pixel-btn-sm danger" @click="confirmDelete(cat)" title="删除">✕</button>
            </div>
          </template>

          <!-- Edit Form (inline) -->
          <template v-else>
            <div class="form-card inline-edit animate-fade-in">
              <div class="form-header">
                <h3 class="form-title">✎ 编辑分类</h3>
                <button class="pixel-btn-close" @click="resetEditForm">✕</button>
              </div>
              <div class="form-body">
                <div class="form-grid">
                  <div class="form-field">
                    <label class="form-label">名称 *</label>
                    <input
                      v-model="editForm.name"
                      type="text"
                      class="pixel-input"
                      placeholder="分类名称"
                      maxlength="30"
                    />
                  </div>
                  <div class="form-field">
                    <label class="form-label">图标</label>
                    <input
                      v-model="editForm.icon"
                      type="text"
                      class="pixel-input icon-input"
                      placeholder="▦"
                      maxlength="4"
                    />
                  </div>
                  <div class="form-field">
                    <label class="form-label">颜色</label>
                    <div class="color-picker-wrap">
                      <input
                        v-model="editForm.color"
                        type="color"
                        class="pixel-color"
                      />
                      <span class="color-value">{{ editForm.color }}</span>
                    </div>
                  </div>
                  <div class="form-field">
                    <label class="form-label">排序</label>
                    <input
                      v-model.number="editForm.sort_order"
                      type="number"
                      class="pixel-input"
                      min="0"
                    />
                  </div>
                </div>
                <div class="form-field">
                  <label class="form-label">父分类</label>
                  <select v-model="editForm.parent_id" class="pixel-select">
                    <option :value="null">— 无 —</option>
                    <option
                      v-for="p in parentOptions"
                      :key="p.id"
                      :value="p.id"
                    >{{ p.icon || '▦' }} {{ p.name }}</option>
                  </select>
                </div>
                <div v-if="editError" class="form-error">{{ editError }}</div>
                <div class="form-actions">
                  <button
                    class="pixel-btn pixel-btn-glow success"
                    @click="handleSave"
                    :disabled="saving"
                  >
                    {{ saving ? '保存中...' : '保存' }}
                  </button>
                  <button class="pixel-btn pixel-btn-glow" @click="resetEditForm">取消</button>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </template>

    <!-- Delete Confirm Modal -->
    <Teleport to="body">
      <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
        <div class="modal-card animate-fade-in">
          <div class="modal-header">
            <span class="modal-icon">!</span>
            <h3 class="modal-title">确认删除</h3>
          </div>
          <div class="modal-body">
            <p class="modal-text">
              确定要删除分类 <strong>{{ deleteTarget.name }}</strong> 吗？
            </p>
            <p class="modal-hint">此操作不可撤销。</p>
            <div v-if="deleteError" class="form-error">{{ deleteError }}</div>
          </div>
          <div class="modal-actions">
            <button
              class="pixel-btn pixel-btn-glow accent"
              @click="handleDelete"
              :disabled="deleting"
            >
              {{ deleting ? '删除中...' : '确认删除' }}
            </button>
            <button class="pixel-btn pixel-btn-glow" @click="deleteTarget = null">取消</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.categories-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ===== Loading / Error ===== */
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

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  gap: 12px;
}

.error-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Press Start 2P', monospace;
  font-size: 24px;
  color: var(--pixel-accent);
  border: 3px solid var(--pixel-accent);
  background: var(--pixel-bg);
}

.error-text {
  font-size: 14px;
  color: var(--pixel-accent);
}

/* ===== Page Header ===== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.page-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 16px;
  color: var(--pixel-primary);
  margin: 0;
}

/* ===== Pixel Button ===== */
.pixel-btn {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  padding: 8px 16px;
  border: 3px solid var(--pixel-border);
  background: var(--pixel-card-bg);
  color: var(--pixel-text);
  cursor: pointer;
  box-shadow: 3px 3px 0 var(--pixel-shadow);
  transition: transform 0.08s ease, box-shadow 0.15s ease, border-color 0.15s ease;
  white-space: nowrap;
  border-radius: 0;
}

.pixel-btn:hover {
  border-color: var(--pixel-text-secondary);
}

.pixel-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

.pixel-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
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

.pixel-btn.accent {
  background: var(--pixel-accent);
  border-color: var(--pixel-accent);
  color: var(--pixel-text);
}

.pixel-btn.accent:hover {
  border-color: var(--pixel-text);
}

.pixel-btn-close {
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
  border-radius: 0;
}

.pixel-btn-close:hover {
  border-color: var(--pixel-accent);
  color: var(--pixel-accent);
}

.pixel-btn-sm {
  font-size: 14px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
  color: var(--pixel-text);
  cursor: pointer;
  padding: 0;
  box-shadow: 2px 2px 0 var(--pixel-shadow);
  border-radius: 0;
  transition: transform 0.05s steps(1), border-color 0.1s steps(2);
}

.pixel-btn-sm:hover {
  border-color: var(--pixel-primary);
}

.pixel-btn-sm:active {
  transform: translate(2px, 2px);
  box-shadow: none;
}

.pixel-btn-sm.danger:hover {
  border-color: var(--pixel-accent);
  color: var(--pixel-accent);
}

/* ===== Form Styles ===== */
.form-card {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  box-shadow: 3px 3px 0 var(--pixel-shadow);
}

.form-card.inline-edit {
  border-color: var(--pixel-primary);
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

.form-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-label {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  color: var(--pixel-text-secondary);
  letter-spacing: 0.5px;
}

.pixel-input {
  font-family: var(--font-pixel);
  font-size: 13px;
  padding: 8px 10px;
  border: 3px solid var(--pixel-border);
  background: var(--pixel-bg);
  color: var(--pixel-text);
  outline: none;
  border-radius: 0;
  width: 100%;
  box-sizing: border-box;
  transition: border-color 0.15s ease, box-shadow 0.25s ease;
}

.pixel-input:focus {
  border-color: var(--pixel-primary);
  box-shadow: 0 0 0 1px var(--pixel-primary), 0 0 8px rgba(65, 166, 246, 0.15);
}

.pixel-input::placeholder {
  color: var(--pixel-text-secondary);
  opacity: 0.6;
}

.icon-input {
  text-align: center;
  font-size: 18px;
}

.pixel-select {
  font-family: var(--font-pixel);
  font-size: 13px;
  padding: 8px 10px;
  border: 3px solid var(--pixel-border);
  background: var(--pixel-bg);
  color: var(--pixel-text);
  outline: none;
  border-radius: 0;
  cursor: pointer;
  width: 100%;
  box-sizing: border-box;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M2 4l4 4 4-4' fill='none' stroke='%2394b0c2' stroke-width='2'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  padding-right: 32px;
}

.pixel-select:focus {
  border-color: var(--pixel-primary);
}

.color-picker-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pixel-color {
  width: 40px;
  height: 36px;
  border: 3px solid var(--pixel-border);
  background: var(--pixel-bg);
  cursor: pointer;
  padding: 2px;
  border-radius: 0;
}

.pixel-color::-webkit-color-swatch-wrapper {
  padding: 0;
}

.pixel-color::-webkit-color-swatch {
  border: none;
  border-radius: 0;
}

.color-value {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  color: var(--pixel-text-secondary);
}

.form-error {
  font-family: var(--font-pixel);
  font-size: 12px;
  color: var(--pixel-accent);
  padding: 8px;
  border: 2px solid var(--pixel-accent);
  background: rgba(177, 62, 83, 0.1);
}

.form-actions {
  display: flex;
  gap: 8px;
  padding-top: 4px;
}

/* ===== Empty State ===== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 16px;
}

.empty-icon {
  font-size: 64px;
  color: var(--pixel-border);
  line-height: 1;
}

.empty-text {
  font-family: 'Press Start 2P', monospace;
  font-size: 12px;
  color: var(--pixel-text-secondary);
}

/* ===== Category Grid ===== */
.category-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.category-card {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  box-shadow: 3px 3px 0 var(--pixel-shadow);
  display: flex;
  flex-direction: column;
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
  overflow: hidden;
}

.category-card:hover {
  border-color: var(--pixel-primary);
  box-shadow: 4px 6px 0 var(--pixel-shadow);
}

.category-card:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

.category-card.editing {
  grid-column: 1 / -1;
  border-color: var(--pixel-primary);
}

.card-icon-area {
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.card-icon {
  font-size: 32px;
  color: rgba(255, 255, 255, 0.9);
  text-shadow: 2px 2px 0 rgba(0, 0, 0, 0.3);
  line-height: 1;
}

.card-body {
  padding: 12px 14px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-name {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  color: var(--pixel-text);
  word-break: break-all;
  line-height: 1.4;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.card-sort {
  font-family: 'Press Start 2P', monospace;
  font-size: 7px;
  color: var(--pixel-text-secondary);
  padding: 2px 4px;
  border: 1px solid var(--pixel-border);
  background: var(--pixel-bg);
}

.card-parent {
  font-size: 11px;
  color: var(--pixel-text-secondary);
}

.card-color-bar {
  height: 4px;
  width: 100%;
}

.card-actions {
  display: flex;
  border-top: 2px solid var(--pixel-border);
}

.card-actions .pixel-btn-sm {
  flex: 1;
  box-shadow: none;
  border: none;
  border-right: 2px solid var(--pixel-border);
  border-radius: 0;
}

.card-actions .pixel-btn-sm:last-child {
  border-right: none;
}

/* ===== Modal ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(26, 28, 44, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-card {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-accent);
  box-shadow: 6px 6px 0 var(--pixel-shadow);
  max-width: 400px;
  width: 100%;
  animation: pixel-scale-in 0.2s ease-out;
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 2px solid var(--pixel-border);
  background: var(--pixel-bg-secondary);
}

.modal-icon {
  font-family: 'Press Start 2P', monospace;
  font-size: 14px;
  color: var(--pixel-accent);
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--pixel-accent);
}

.modal-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  color: var(--pixel-accent);
  margin: 0;
}

.modal-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.modal-text {
  font-size: 14px;
  color: var(--pixel-text);
  margin: 0;
}

.modal-text strong {
  color: var(--pixel-accent);
}

.modal-hint {
  font-size: 12px;
  color: var(--pixel-text-secondary);
  margin: 0;
}

.modal-actions {
  display: flex;
  gap: 8px;
  padding: 0 16px 16px;
  justify-content: flex-end;
}

/* ===== Responsive ===== */
@media (max-width: 1024px) {
  .category-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .category-grid {
    grid-template-columns: 1fr;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .modal-card {
    max-width: 100%;
  }
}
</style>
