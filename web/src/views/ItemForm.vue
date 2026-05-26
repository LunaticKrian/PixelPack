<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { createItem, updateItem, getItem, uploadImage, deleteImage } from '../api/items'
import { listCategories, listTags } from '../api/metadata'
import type { Item, Category, Tag, ItemImage } from '../types/item'

const router = useRouter()
const route = useRoute()

const isEdit = computed(() => !!route.params.id)
const itemId = computed(() => route.params.id ? Number(route.params.id) : null)
const pageTitle = computed(() => isEdit.value ? 'EDIT ITEM' : 'NEW ITEM')
const pageIcon = computed(() => isEdit.value ? '✎' : '▶')

// Metadata
const categories = ref<Category[]>([])
const tags = ref<Tag[]>([])

// Form state
const loading = ref(false)
const pageLoading = ref(false)
const error = ref('')
const uploadProgress = ref(false)

// Form fields
const form = ref({
  name: '',
  description: '',
  category_id: null as number | null,
  purchase_date: '',
  purchase_price: '',
  currency: 'CNY',
  purchase_channel: '',
  current_value: '',
  warranty_expiry: '',
  expected_lifespan: '',
  usage_count: '',
  tag_ids: [] as number[],
})

const existingImages = ref<ItemImage[]>([])
const newFiles = ref<{ file: File; preview: string }[]>([])

// Validation
const errors = ref<Record<string, string>>({})

function validate(): boolean {
  errors.value = {}
  if (!form.value.name.trim()) {
    errors.value.name = '物品名称不能为空'
  }
  if (!form.value.purchase_date) {
    errors.value.purchase_date = '购买日期不能为空'
  }
  if (!form.value.purchase_price || Number(form.value.purchase_price) <= 0) {
    errors.value.purchase_price = '购买价格必须大于 0'
  }
  return Object.keys(errors.value).length === 0
}

// Load metadata
async function loadMetadata() {
  try {
    const [catsData, tagsData] = await Promise.all([
      listCategories(),
      listTags(),
    ])
    categories.value = catsData
    tags.value = tagsData
  } catch (e: any) {
    error.value = '加载分类/标签失败'
  }
}

// Load item for edit
async function loadItem() {
  if (!itemId.value) return
  pageLoading.value = true
  try {
    const item = await getItem(itemId.value)
    form.value = {
      name: item.name,
      description: item.description || '',
      category_id: item.category_id,
      purchase_date: item.purchase_date ? item.purchase_date.slice(0, 10) : '',
      purchase_price: String(item.purchase_price),
      currency: item.currency || 'CNY',
      purchase_channel: item.purchase_channel || '',
      current_value: item.current_value != null ? String(item.current_value) : '',
      warranty_expiry: item.warranty_expiry ? item.warranty_expiry.slice(0, 10) : '',
      expected_lifespan: item.expected_lifespan != null ? String(item.expected_lifespan) : '',
      usage_count: item.usage_count != null ? String(item.usage_count) : '',
      tag_ids: [],
    }
    // Note: tags would need a separate endpoint or be included in item response
    // For now we load tag_ids if available
    existingImages.value = []
  } catch (e: any) {
    error.value = e?.data?.detail || '加载物品信息失败'
  } finally {
    pageLoading.value = false
  }
}

// Image handling
const fileInput = ref<HTMLInputElement | null>(null)

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files) return
  for (const file of target.files) {
    if (!file.type.startsWith('image/')) continue
    const preview = URL.createObjectURL(file)
    newFiles.value.push({ file, preview })
  }
  target.value = ''
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  if (!event.dataTransfer?.files) return
  for (const file of event.dataTransfer.files) {
    if (!file.type.startsWith('image/')) continue
    const preview = URL.createObjectURL(file)
    newFiles.value.push({ file, preview })
  }
}

function handleDragOver(event: DragEvent) {
  event.preventDefault()
}

function removeNewFile(index: number) {
  const item = newFiles.value[index]
  URL.revokeObjectURL(item.preview)
  newFiles.value.splice(index, 1)
}

async function removeExistingImage(imageId: number) {
  try {
    await deleteImage(imageId)
    existingImages.value = existingImages.value.filter(img => img.id !== imageId)
  } catch (e: any) {
    error.value = '删除图片失败'
  }
}

// Submit
async function handleSubmit() {
  if (!validate()) return
  loading.value = true
  error.value = ''

  try {
    const payload: Partial<Item> = {
      name: form.value.name.trim(),
      description: form.value.description.trim() || null,
      category_id: form.value.category_id,
      purchase_date: form.value.purchase_date,
      purchase_price: Number(form.value.purchase_price),
      currency: form.value.currency,
      purchase_channel: form.value.purchase_channel.trim() || null,
      current_value: form.value.current_value ? Number(form.value.current_value) : null,
      warranty_expiry: form.value.warranty_expiry || null,
      expected_lifespan: form.value.expected_lifespan ? Number(form.value.expected_lifespan) : null,
      usage_count: form.value.usage_count ? Number(form.value.usage_count) : null,
    }

    let savedItem: Item
    if (isEdit.value && itemId.value) {
      savedItem = await updateItem(itemId.value, payload)
    } else {
      savedItem = await createItem(payload)
    }

    // Upload new images
    if (newFiles.value.length > 0) {
      uploadProgress.value = true
      for (const { file } of newFiles.value) {
        try {
          await uploadImage(savedItem.id, file)
        } catch {
          // Continue uploading remaining files even if one fails
        }
      }
      uploadProgress.value = false
    }

    router.push({ name: 'item-detail', params: { id: savedItem.id } })
  } catch (e: any) {
    error.value = e?.data?.detail || '保存失败，请重试'
  } finally {
    loading.value = false
    uploadProgress.value = false
  }
}

function handleCancel() {
  router.push({ name: 'items' })
}

function toggleTag(tagId: number) {
  const idx = form.value.tag_ids.indexOf(tagId)
  if (idx >= 0) {
    form.value.tag_ids.splice(idx, 1)
  } else {
    form.value.tag_ids.push(tagId)
  }
}

onMounted(async () => {
  await loadMetadata()
  if (isEdit.value) {
    await loadItem()
  }
})
</script>

<template>
  <div class="item-form-page">
    <!-- Page loading -->
    <div v-if="pageLoading" class="loading-container">
      <div class="pixel-loading"></div>
      <p class="loading-text">LOADING...</p>
    </div>

    <template v-else>
      <!-- Title -->
      <div class="form-header">
        <h1 class="form-title">
          <span class="title-icon">{{ pageIcon }}</span>
          {{ pageTitle }}
        </h1>
      </div>

      <!-- Error message -->
      <div v-if="error" class="error-msg">
        <span class="error-icon">!</span>
        {{ error }}
      </div>

      <form class="form-card pixel-card-hover" @submit.prevent="handleSubmit">
        <!-- Section 1: Basic Info -->
        <section class="form-section">
          <h2 class="section-title">— 基本信息 —</h2>

          <div class="field">
            <label class="field-label">
              <span class="label-bracket">[</span>NAME<span class="label-bracket">]</span>
              <span class="required">*</span>
            </label>
            <input
              v-model="form.name"
              type="text"
              class="pixel-input"
              placeholder="输入物品名称..."
              maxlength="100"
            />
            <span v-if="errors.name" class="field-error">{{ errors.name }}</span>
          </div>

          <div class="field">
            <label class="field-label">
              <span class="label-bracket">[</span>DESCRIPTION<span class="label-bracket">]</span>
            </label>
            <textarea
              v-model="form.description"
              class="pixel-input pixel-textarea"
              placeholder="物品描述（可选）..."
              rows="3"
            ></textarea>
          </div>

          <div class="field">
            <label class="field-label">
              <span class="label-bracket">[</span>CATEGORY<span class="label-bracket">]</span>
            </label>
            <select v-model="form.category_id" class="pixel-input pixel-select">
              <option :value="null">— 选择分类 —</option>
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                {{ cat.icon ? cat.icon + ' ' : '' }}{{ cat.name }}
              </option>
            </select>
          </div>
        </section>

        <!-- Section 2: Purchase Info -->
        <section class="form-section">
          <h2 class="section-title">— 购买信息 —</h2>

          <div class="field">
            <label class="field-label">
              <span class="label-bracket">[</span>PURCHASE DATE<span class="label-bracket">]</span>
              <span class="required">*</span>
            </label>
            <input
              v-model="form.purchase_date"
              type="date"
              class="pixel-input pixel-date"
            />
            <span v-if="errors.purchase_date" class="field-error">{{ errors.purchase_date }}</span>
          </div>

          <div class="inline-group">
            <div class="field flex-grow">
              <label class="field-label">
                <span class="label-bracket">[</span>PRICE<span class="label-bracket">]</span>
                <span class="required">*</span>
              </label>
              <input
                v-model="form.purchase_price"
                type="number"
                class="pixel-input"
                placeholder="0.00"
                step="0.01"
                min="0"
              />
              <span v-if="errors.purchase_price" class="field-error">{{ errors.purchase_price }}</span>
            </div>

            <div class="field field-currency">
              <label class="field-label">
                <span class="label-bracket">[</span>CURRENCY<span class="label-bracket">]</span>
              </label>
              <select v-model="form.currency" class="pixel-input pixel-select">
                <option value="CNY">CNY ¥</option>
                <option value="USD">USD $</option>
                <option value="EUR">EUR €</option>
                <option value="JPY">JPY ¥</option>
              </select>
            </div>
          </div>

          <div class="field">
            <label class="field-label">
              <span class="label-bracket">[</span>CHANNEL<span class="label-bracket">]</span>
            </label>
            <input
              v-model="form.purchase_channel"
              type="text"
              class="pixel-input"
              placeholder="购买渠道（可选）..."
              maxlength="100"
            />
          </div>
        </section>

        <!-- Section 3: Extra Info -->
        <section class="form-section">
          <h2 class="section-title">— 附加信息 —</h2>

          <div class="inline-group">
            <div class="field flex-grow">
              <label class="field-label">
                <span class="label-bracket">[</span>CURRENT VALUE<span class="label-bracket">]</span>
              </label>
              <input
                v-model="form.current_value"
                type="number"
                class="pixel-input"
                placeholder="当前价值（可选）"
                step="0.01"
                min="0"
              />
            </div>

            <div class="field flex-grow">
              <label class="field-label">
                <span class="label-bracket">[</span>USAGE COUNT<span class="label-bracket">]</span>
              </label>
              <input
                v-model="form.usage_count"
                type="number"
                class="pixel-input"
                placeholder="使用次数"
                min="0"
              />
            </div>
          </div>

          <div class="inline-group">
            <div class="field flex-grow">
              <label class="field-label">
                <span class="label-bracket">[</span>WARRANTY EXPIRY<span class="label-bracket">]</span>
              </label>
              <input
                v-model="form.warranty_expiry"
                type="date"
                class="pixel-input pixel-date"
              />
            </div>

            <div class="field flex-grow">
              <label class="field-label">
                <span class="label-bracket">[</span>LIFESPAN (DAYS)<span class="label-bracket">]</span>
              </label>
              <input
                v-model="form.expected_lifespan"
                type="number"
                class="pixel-input"
                placeholder="预期寿命"
                min="0"
              />
            </div>
          </div>
        </section>

        <!-- Section 4: Tags -->
        <section class="form-section">
          <h2 class="section-title">— 标签 —</h2>

          <div v-if="tags.length === 0" class="empty-hint">
            暂无标签，请先在标签管理中创建
          </div>
          <div v-else class="tags-grid">
            <label
              v-for="tag in tags"
              :key="tag.id"
              class="tag-checkbox"
              :class="{ active: form.tag_ids.includes(tag.id) }"
            >
              <input
                type="checkbox"
                :checked="form.tag_ids.includes(tag.id)"
                class="tag-input-hidden"
                @change="toggleTag(tag.id)"
              />
              <span class="tag-box">■</span>
              <span class="tag-name">{{ tag.name }}</span>
            </label>
          </div>
        </section>

        <!-- Section 5: Images -->
        <section class="form-section">
          <h2 class="section-title">— 图片 —</h2>

          <!-- Existing images (edit mode) -->
          <div v-if="existingImages.length > 0" class="image-grid">
            <div v-for="img in existingImages" :key="img.id" class="image-thumb">
              <img :src="img.url" :alt="'Image ' + img.id" />
              <button
                type="button"
                class="image-delete"
                title="删除图片"
                @click="removeExistingImage(img.id)"
              >✕</button>
            </div>
          </div>

          <!-- New image previews -->
          <div v-if="newFiles.length > 0" class="image-grid">
            <div v-for="(item, index) in newFiles" :key="'new-' + index" class="image-thumb">
              <img :src="item.preview" :alt="'New image ' + (index + 1)" />
              <button
                type="button"
                class="image-delete"
                title="移除图片"
                @click="removeNewFile(index)"
              >✕</button>
            </div>
          </div>

          <!-- Upload area -->
          <div
            class="upload-area"
            @click="triggerFileInput"
            @drop="handleDrop"
            @dragover="handleDragOver"
          >
            <div v-if="uploadProgress" class="pixel-loading"></div>
            <template v-else>
              <div class="upload-icon">📤</div>
              <p class="upload-text">DROP IMAGE HERE</p>
              <p class="upload-subtext">or click to browse</p>
            </template>
          </div>
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            multiple
            class="hidden-input"
            @change="handleFileSelect"
          />
        </section>

        <!-- Action buttons -->
        <div class="form-actions">
          <button type="submit" class="btn-save pixel-btn-glow" :disabled="loading">
            <span v-if="loading" class="pixel-loading inline"></span>
            <span v-else>▶ SAVE</span>
          </button>
          <button type="button" class="btn-cancel" :disabled="loading" @click="handleCancel">
            ✕ CANCEL
          </button>
        </div>
      </form>
    </template>
  </div>
</template>

<style scoped>
.item-form-page {
  max-width: 680px;
  margin: 0 auto;
  padding: 24px 16px 48px;
  animation: pixel-fade-in 0.3s steps(4);
}

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 16px;
}

.loading-text {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  color: var(--pixel-text-secondary);
  animation: pixel-blink 1s step-end infinite;
}

/* Header */
.form-header {
  margin-bottom: 20px;
}

.form-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 14px;
  color: var(--pixel-primary);
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-icon {
  color: var(--pixel-accent);
}

/* Error */
.error-msg {
  background: rgba(255, 107, 107, 0.1);
  border: 2px solid var(--pixel-accent);
  color: var(--pixel-accent);
  font-family: var(--font-pixel);
  font-size: 12px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.error-icon {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--pixel-accent);
  color: var(--pixel-bg);
  flex-shrink: 0;
}

/* Form card */
.form-card {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  box-shadow: 4px 4px 0 var(--pixel-shadow);
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: border-color 0.15s ease;
}

/* Sections */
.form-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-bottom: 20px;
  border-bottom: 2px dashed var(--pixel-border);
  margin-bottom: 12px;
}

.form-section:last-of-type {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.section-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  color: var(--pixel-text-secondary);
  letter-spacing: 1px;
  margin: 0;
}

/* Fields */
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  color: var(--pixel-text-secondary);
  letter-spacing: 1px;
}

.label-bracket {
  color: var(--pixel-border);
}

.required {
  color: var(--pixel-accent);
  margin-left: 4px;
}

.field-error {
  font-family: var(--font-pixel);
  font-size: 12px;
  color: var(--pixel-accent);
}

.pixel-input {
  background: var(--pixel-bg);
  border: 3px solid var(--pixel-border);
  color: var(--pixel-text);
  font-family: var(--font-pixel);
  font-size: 14px;
  padding: 10px 12px;
  outline: none;
  width: 100%;
  box-sizing: border-box;
}

.pixel-input:focus {
  border-color: var(--pixel-primary);
  box-shadow: 0 0 0 1px var(--pixel-primary), 0 0 8px rgba(65, 166, 246, 0.15);
  transition: border-color 0.15s ease, box-shadow 0.25s ease;
}

.pixel-input::placeholder {
  color: var(--pixel-text-secondary);
  opacity: 0.5;
}

.pixel-textarea {
  resize: vertical;
  min-height: 72px;
  line-height: 1.5;
}

.pixel-select {
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' fill='%23A0A0B0'%3E%3Cpath d='M0 0l6 8 6-8z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 36px;
  cursor: pointer;
}

.pixel-select option {
  background: var(--pixel-card-bg);
  color: var(--pixel-text);
}

.pixel-date {
  color-scheme: dark;
}

/* Inline group */
.inline-group {
  display: flex;
  gap: 12px;
}

.flex-grow {
  flex: 1;
  min-width: 0;
}

.field-currency {
  min-width: 130px;
  flex: 0 0 130px;
}

/* Tags */
.empty-hint {
  font-family: var(--font-pixel);
  font-size: 13px;
  color: var(--pixel-text-secondary);
  opacity: 0.6;
}

.tags-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
  cursor: pointer;
  font-family: var(--font-pixel);
  font-size: 13px;
  color: var(--pixel-text-secondary);
  transition: border-color 0.12s ease, background 0.12s ease, color 0.12s ease;
  user-select: none;
}

.tag-checkbox:hover {
  border-color: var(--pixel-primary);
}

.tag-checkbox.active {
  border-color: var(--pixel-primary);
  background: rgba(60, 187, 177, 0.15);
  color: var(--pixel-primary);
}

.tag-input-hidden {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.tag-box {
  font-size: 10px;
  color: var(--pixel-border);
}

.tag-checkbox.active .tag-box {
  color: var(--pixel-primary);
}

.tag-name {
  font-family: var(--font-pixel);
}

/* Image upload */
.image-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.image-thumb {
  position: relative;
  width: 80px;
  height: 80px;
  border: 2px solid var(--pixel-border);
  overflow: hidden;
}

.image-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.image-delete {
  position: absolute;
  top: 0;
  right: 0;
  width: 20px;
  height: 20px;
  background: var(--pixel-accent);
  color: var(--pixel-bg);
  border: none;
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  padding: 0;
}

.image-delete:hover {
  background: #ff4040;
}

.upload-area {
  border: 3px dashed var(--pixel-border);
  padding: 32px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.upload-area:hover {
  border-color: var(--pixel-primary);
  background: rgba(60, 187, 177, 0.05);
}

.upload-icon {
  font-size: 24px;
  line-height: 1;
}

.upload-text {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  color: var(--pixel-text-secondary);
  margin: 0;
}

.upload-subtext {
  font-family: var(--font-pixel);
  font-size: 12px;
  color: var(--pixel-text-secondary);
  opacity: 0.5;
  margin: 0;
}

.hidden-input {
  display: none;
}

/* Actions */
.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  padding-top: 20px;
}

.btn-save {
  background: var(--pixel-primary);
  border: 3px solid #2a8f87;
  color: var(--pixel-bg);
  font-family: 'Press Start 2P', monospace;
  font-size: 12px;
  padding: 14px 28px;
  cursor: pointer;
  box-shadow: 3px 3px 0 var(--pixel-shadow);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-width: 160px;
  transition: transform 0.08s ease, box-shadow 0.15s ease, background 0.15s ease;
}

.btn-save:hover {
  background: #4ecdc4;
  box-shadow: 3px 3px 0 var(--pixel-shadow), 0 0 8px rgba(65, 166, 246, 0.3);
}

.btn-save:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  background: transparent;
  border: 3px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  font-family: 'Press Start 2P', monospace;
  font-size: 12px;
  padding: 14px 28px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-cancel:hover {
  border-color: var(--pixel-accent);
  color: var(--pixel-accent);
}

.btn-cancel:active {
  transform: translate(1px, 1px);
}

.btn-cancel:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Inline spinner */
.inline {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-width: 2px;
}

/* Responsive */
@media (max-width: 520px) {
  .item-form-page {
    padding: 16px 8px 32px;
  }

  .form-card {
    padding: 20px 14px;
  }

  .inline-group {
    flex-direction: column;
  }

  .field-currency {
    flex: 1;
    min-width: auto;
  }

  .form-actions {
    flex-direction: column;
  }

  .btn-save,
  .btn-cancel {
    width: 100%;
    justify-content: center;
  }
}
</style>
