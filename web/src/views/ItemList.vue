<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listItems, type ItemListParams } from '../api/items'
import { listCategories, listTags } from '../api/metadata'
import type { Item, Category, Tag } from '../types/item'
import type { PaginatedResponse } from '../types/api'
import { formatCurrency, formatDays } from '../utils/format'

const router = useRouter()

// --- State ---
const items = ref<Item[]>([])
const categories = ref<Category[]>([])
const tags = ref<Tag[]>([])
const loading = ref(true)
const error = ref('')

// --- Filters ---
const keyword = ref('')
const filterCategory = ref<number | ''>('')
const filterStatus = ref<string>('')
const filterTag = ref<number | ''>('')
const sortBy = ref('')

// --- Pagination ---
const currentPage = ref(1)
const totalPages = ref(1)
const totalItems = ref(0)
const pageSize = 12

// --- Status display map ---
const statusMap: Record<string, { label: string; color: string }> = {
  ACTIVE: { label: '使用中', color: 'var(--pixel-success)' },
  IDLE: { label: '闲置', color: 'var(--pixel-warning)' },
  RETIRED: { label: '退役', color: 'var(--pixel-text-secondary)' },
  SOLD: { label: '已售', color: 'var(--pixel-info)' },
  DISCARDED: { label: '已弃', color: 'var(--pixel-accent)' },
}

// --- Sort options map ---
const sortOptions: Record<string, { sort_by: string; order: string }> = {
  '': { sort_by: 'created_at', order: 'desc' },
  newest: { sort_by: 'created_at', order: 'desc' },
  daily_asc: { sort_by: 'daily_cost', order: 'asc' },
  daily_desc: { sort_by: 'daily_cost', order: 'desc' },
  price_asc: { sort_by: 'purchase_price', order: 'asc' },
  price_desc: { sort_by: 'purchase_price', order: 'desc' },
  usage_desc: { sort_by: 'usage_days', order: 'desc' },
}

// --- Category name lookup ---
function getCategoryName(categoryId: number | null): string {
  if (!categoryId) return ''
  const cat = categories.value.find(c => c.id === categoryId)
  return cat ? cat.name : ''
}

// --- Fetch items ---
async function fetchItems() {
  loading.value = true
  error.value = ''

  const sortConfig = sortOptions[sortBy.value] || sortOptions['']
  const params: ItemListParams = {
    page: currentPage.value,
    page_size: pageSize,
    sort_by: sortConfig.sort_by,
    order: sortConfig.order,
  }

  if (keyword.value.trim()) params.keyword = keyword.value.trim()
  if (filterCategory.value !== '') params.category_id = filterCategory.value
  if (filterStatus.value !== '') params.status = filterStatus.value
  if (filterTag.value !== '') params.tag_id = filterTag.value

  try {
    const res = await listItems(params) as PaginatedResponse<Item>
    items.value = res.items || []
    totalItems.value = res.total
    totalPages.value = res.pages
    currentPage.value = res.page
  } catch (e: any) {
    error.value = e?.data?.detail || '加载物品列表失败'
  } finally {
    loading.value = false
  }
}

// --- Fetch metadata (categories + tags) ---
async function fetchMetadata() {
  try {
    const [cats, tagList] = await Promise.all([listCategories(), listTags()])
    categories.value = cats as Category[]
    tags.value = tagList as Tag[]
  } catch {
    // silent fail for metadata
  }
}

// --- Reset page when filters change ---
watch([keyword, filterCategory, filterStatus, filterTag, sortBy], () => {
  currentPage.value = 1
  fetchItems()
})

// --- Pagination ---
function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  fetchItems()
}

// --- Navigation ---
function goToItem(id: number) {
  router.push(`/items/${id}`)
}

function goToAddItem() {
  router.push('/items/new')
}

// --- Debounced search ---
let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    fetchItems()
  }, 400)
}

// --- Init ---
onMounted(() => {
  fetchMetadata()
  fetchItems()
})
</script>

<template>
  <div class="item-list-page animate-fade-in">
    <!-- Page Header -->
    <div class="page-header">
      <h1 class="page-title">
        <span class="title-icon">◆</span>
        <span>物品列表</span>
      </h1>
      <button class="add-btn" @click="goToAddItem">
        <span>+ 添加物品</span>
      </button>
    </div>

    <!-- Search & Filters -->
    <div class="filter-bar">
      <div class="search-wrap">
        <span class="search-icon">◎</span>
        <input
          v-model="keyword"
          type="text"
          class="pixel-input search-input"
          placeholder="搜索物品..."
          @input="onSearchInput"
        />
      </div>

      <div class="filter-row">
        <select v-model="filterCategory" class="pixel-input filter-select">
          <option value="">全部分类</option>
          <option v-for="cat in categories" :key="cat.id" :value="cat.id">
            {{ cat.icon }} {{ cat.name }}
          </option>
        </select>

        <select v-model="filterStatus" class="pixel-input filter-select">
          <option value="">全部状态</option>
          <option value="ACTIVE">使用中</option>
          <option value="IDLE">闲置</option>
          <option value="RETIRED">退役</option>
          <option value="SOLD">已售</option>
          <option value="DISCARDED">已弃</option>
        </select>

        <select v-model="filterTag" class="pixel-input filter-select">
          <option value="">全部标签</option>
          <option v-for="tag in tags" :key="tag.id" :value="tag.id">
            {{ tag.name }}
          </option>
        </select>

        <select v-model="sortBy" class="pixel-input filter-select">
          <option value="">最近添加</option>
          <option value="daily_asc">日均成本↑</option>
          <option value="daily_desc">日均成本↓</option>
          <option value="price_asc">价格↑</option>
          <option value="price_desc">价格↓</option>
          <option value="usage_desc">使用天数↓</option>
        </select>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="pixel-loading"></div>
      <p class="loading-text">加载中...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <span class="error-icon">!</span>
      <p>{{ error }}</p>
      <button class="retry-btn" @click="fetchItems">重试</button>
    </div>

    <!-- Empty State -->
    <div v-else-if="items.length === 0" class="empty-state">
      <span class="empty-icon">▢</span>
      <p class="empty-text">还没有物品</p>
      <button class="add-btn" @click="goToAddItem">添加物品</button>
    </div>

    <!-- Item Grid -->
    <div v-else class="item-grid">
      <div
        v-for="item in items"
        :key="item.id"
        class="item-card"
        @click="goToItem(item.id)"
      >
        <!-- Thumbnail -->
        <div class="card-thumbnail">
          <img
            v-if="item.images && item.images.length > 0"
            :src="item.images[0].url"
            :alt="item.name"
            class="thumbnail-img"
          />
          <span v-else class="thumbnail-placeholder">◆</span>
        </div>

        <!-- Card Body -->
        <div class="card-body">
          <div class="card-header">
            <h3 class="card-name">{{ item.name }}</h3>
            <span
              class="status-badge"
              :style="{ color: statusMap[item.status]?.color, borderColor: statusMap[item.status]?.color }"
            >
              {{ statusMap[item.status]?.label || item.status }}
            </span>
          </div>

          <!-- Key Stats -->
          <div class="card-stats">
            <div class="stat">
              <span class="stat-label">日均</span>
              <span class="stat-value stat-primary">{{ formatCurrency(item.daily_cost) }}</span>
            </div>
            <div class="stat">
              <span class="stat-label">使用</span>
              <span class="stat-value stat-secondary">{{ formatDays(item.usage_days) }}</span>
            </div>
          </div>

          <!-- Footer: Category + Tags -->
          <div class="card-footer">
            <span v-if="getCategoryName(item.category_id)" class="category-label">
              {{ getCategoryName(item.category_id) }}
            </span>
            <div v-if="item.tags && item.tags.length" class="tag-list">
              <span
                v-for="tag in item.tags.slice(0, 3)"
                :key="tag.id"
                class="tag-badge"
                :style="{ borderColor: tag.color || 'var(--pixel-border)' }"
              >
                {{ tag.name }}
              </span>
              <span v-if="item.tags.length > 3" class="tag-badge tag-more">
                +{{ item.tags.length - 3 }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="!loading && items.length > 0" class="pagination">
      <button
        class="page-btn"
        :disabled="currentPage <= 1"
        @click="goToPage(currentPage - 1)"
      >
        ◀ 上一页
      </button>
      <span class="page-info">
        第 {{ currentPage }} 页 / 共 {{ totalPages }} 页
      </span>
      <button
        class="page-btn"
        :disabled="currentPage >= totalPages"
        @click="goToPage(currentPage + 1)"
      >
        下一页 ▶
      </button>
    </div>
  </div>
</template>

<style scoped>
.item-list-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  box-sizing: border-box;
}

/* === Page Header === */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.page-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 16px;
  color: var(--pixel-primary);
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
}

.title-icon {
  font-size: 20px;
}

.add-btn {
  background: var(--pixel-primary);
  border: 3px solid #2a8f87;
  color: var(--pixel-bg);
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  padding: 10px 16px;
  cursor: pointer;
  box-shadow: 3px 3px 0 var(--pixel-shadow);
  transition: none;
}

.add-btn:hover {
  background: #4ecdc4;
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.4);
}

.add-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

/* === Filter Bar === */
.filter-bar {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.search-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 16px;
  color: var(--pixel-text-secondary);
  pointer-events: none;
  z-index: 1;
}

.search-input {
  padding-left: 36px;
}

.filter-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

/* === Pixel Input (shared) === */
.pixel-input {
  background: var(--pixel-bg);
  border: 3px solid var(--pixel-border);
  color: var(--pixel-text);
  font-family: var(--font-pixel);
  font-size: 13px;
  padding: 9px 12px;
  outline: none;
  box-sizing: border-box;
}

.pixel-input:focus {
  border-color: var(--pixel-primary);
  box-shadow: 0 0 0 1px var(--pixel-primary);
}

.pixel-input::placeholder {
  color: var(--pixel-text-secondary);
  opacity: 0.5;
}

.filter-select {
  flex: 1;
  min-width: 140px;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23A0A0B0'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 30px;
}

.filter-select option {
  background: var(--pixel-bg);
  color: var(--pixel-text);
}

/* === Loading State === */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  gap: 16px;
}

.loading-text {
  color: var(--pixel-text-secondary);
  font-size: 13px;
  font-family: var(--font-pixel);
}

/* === Error State === */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  gap: 12px;
}

.error-state p {
  color: var(--pixel-accent);
  font-size: 13px;
}

.error-state .error-icon {
  font-family: 'Press Start 2P', monospace;
  font-size: 12px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--pixel-accent);
  color: var(--pixel-bg);
}

.retry-btn {
  background: transparent;
  border: 2px solid var(--pixel-accent);
  color: var(--pixel-accent);
  font-family: var(--font-pixel);
  font-size: 12px;
  padding: 6px 16px;
  cursor: pointer;
}

.retry-btn:hover {
  background: var(--pixel-accent);
  color: var(--pixel-bg);
}

/* === Empty State === */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  gap: 16px;
}

.empty-icon {
  font-size: 64px;
  color: var(--pixel-border);
  line-height: 1;
}

.empty-text {
  color: var(--pixel-text-secondary);
  font-family: 'Press Start 2P', monospace;
  font-size: 12px;
}

/* === Item Grid === */
.item-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

@media (max-width: 1024px) {
  .item-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .item-grid {
    grid-template-columns: 1fr;
  }

  .filter-row {
    flex-direction: column;
  }

  .filter-select {
    min-width: 100%;
  }

  .item-list-page {
    padding: 16px 12px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }
}

/* === Item Card === */
.item-card {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  cursor: pointer;
  box-shadow: 3px 3px 0 var(--pixel-shadow);
  transition: border-color 0.1s steps(2), box-shadow 0.1s steps(2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.item-card:hover {
  border-color: var(--pixel-primary);
  box-shadow: 4px 4px 0 var(--pixel-shadow);
}

.item-card:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

/* --- Card Thumbnail --- */
.card-thumbnail {
  width: 100%;
  height: 140px;
  background: var(--pixel-bg);
  border-bottom: 3px solid var(--pixel-border);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.thumbnail-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumbnail-placeholder {
  font-size: 48px;
  color: var(--pixel-border);
}

/* --- Card Body --- */
.card-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  flex: 1;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.card-name {
  font-family: var(--font-pixel);
  font-size: 14px;
  font-weight: 700;
  color: var(--pixel-text);
  margin: 0;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.status-badge {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  padding: 3px 6px;
  border: 2px solid;
  white-space: nowrap;
  flex-shrink: 0;
  line-height: 1.4;
}

/* --- Card Stats --- */
.card-stats {
  display: flex;
  gap: 12px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-family: 'Press Start 2P', monospace;
  font-size: 7px;
  color: var(--pixel-text-secondary);
  letter-spacing: 0.5px;
}

.stat-value {
  font-family: var(--font-pixel);
  font-size: 13px;
  font-weight: 700;
}

.stat-primary {
  color: var(--pixel-primary);
}

.stat-secondary {
  color: var(--pixel-text-secondary);
}

/* --- Card Footer --- */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  flex-wrap: wrap;
  border-top: 2px solid var(--pixel-border);
  padding-top: 8px;
  margin-top: auto;
}

.category-label {
  font-family: var(--font-pixel);
  font-size: 11px;
  color: var(--pixel-text-secondary);
  padding: 2px 6px;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
}

.tag-list {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.tag-badge {
  font-family: var(--font-pixel);
  font-size: 10px;
  padding: 1px 5px;
  border: 2px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  background: var(--pixel-bg);
}

.tag-more {
  color: var(--pixel-text-secondary);
  opacity: 0.6;
}

/* === Pagination === */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 16px 0;
  border-top: 3px solid var(--pixel-border);
}

.page-btn {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  color: var(--pixel-text);
  font-family: var(--font-pixel);
  font-size: 12px;
  padding: 8px 14px;
  cursor: pointer;
  box-shadow: 2px 2px 0 var(--pixel-shadow);
}

.page-btn:hover:not(:disabled) {
  border-color: var(--pixel-primary);
  color: var(--pixel-primary);
}

.page-btn:active:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

.page-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.page-info {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  color: var(--pixel-text-secondary);
}
</style>
