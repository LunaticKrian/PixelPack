<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listItems, getItem, createItem, updateItem, uploadImage, deleteImage, listTrashedItems, restoreItem, permanentDeleteItem, type ItemListParams } from '../api/items'
import { listCategories, listTags } from '../api/metadata'
import { getOverview, getByCategory, getRecentItems, getWarrantyAlerts, type OverviewStats, type CategoryStat, type RecentItem, type WarrantyAlert } from '../api/stats'
import type { Item, Category, Tag, ItemImage, AdditionalCost } from '../types/item'
import type { PaginatedResponse } from '../types/api'
import { formatCurrency, formatDays } from '../utils/format'
import { exportItemsCSV } from '../utils/export'
import { reportProgress } from '../api/quests'
import Categories from './Categories.vue'
import Tags from './Tags.vue'
import Stats from './Stats.vue'
import PixelSelect from '../components/PixelSelect.vue'
import PixelDatePicker from '../components/PixelDatePicker.vue'
import { useNotifyStore } from '../stores/notification'
import { useAuthStore } from '../stores/auth'

const notify = useNotifyStore()
const auth = useAuthStore()

const categoryOptions = computed(() =>
  categories.value.map(c => ({ value: c.id, label: (c.icon ? c.icon + ' ' : '') + c.name }))
)
const statusOptions = [
  { value: 'ACTIVE', label: '使用中' },
  { value: 'IDLE', label: '闲置' },
  { value: 'RETIRED', label: '退役' },
  { value: 'SOLD', label: '已售' },
  { value: 'DISCARDED', label: '已弃' },
]
const tagOptions = computed(() =>
  tags.value.map(t => ({ value: t.id, label: t.name }))
)
const currencyOptions = [
  { value: 'CNY', label: 'CNY ¥' },
  { value: 'USD', label: 'USD $' },
  { value: 'EUR', label: 'EUR €' },
  { value: 'JPY', label: 'JPY ¥' },
]

const router = useRouter()

// --- State ---
const items = ref<Item[]>([])
const categories = ref<Category[]>([])
const tags = ref<Tag[]>([])
const overview = ref<OverviewStats | null>(null)
const categoryStats = ref<CategoryStat[]>([])
const recentItems = ref<RecentItem[]>([])
const warrantyAlerts = ref<WarrantyAlert[]>([])

// --- Status distribution ---
const statusList = computed(() => [
  { key: 'ACTIVE', label: '使用中', color: 'var(--pixel-success)', count: overview.value?.active_items ?? 0 },
  { key: 'IDLE', label: '闲置', color: 'var(--pixel-warning)', count: (overview.value?.total_items ?? 0) - (overview.value?.active_items ?? 0) },
])

// --- Expandable sections ---
const expandedSections = ref<Record<string, boolean>>({ overview: true, status: true, category: true, recent: false, warranty: false })

function toggleSection(key: string) {
  expandedSections.value[key] = !expandedSections.value[key]
}const loading = ref(true)
const error = ref('')

// --- Filters ---
const keyword = ref('')
const filterCategory = ref<number | ''>('')
const filterStatus = ref<string>('')
const filterTag = ref<number | ''>('')

// --- Pagination ---
const currentPage = ref(1)
const totalPages = ref(1)
const totalItems = ref(0)
const pageSize = 20

// --- Status display map ---
const statusMap: Record<string, { label: string; color: string }> = {
  ACTIVE: { label: '使用中', color: 'var(--pixel-success)' },
  IDLE: { label: '闲置', color: 'var(--pixel-warning)' },
  RETIRED: { label: '退役', color: 'var(--pixel-text-secondary)' },
  SOLD: { label: '已售', color: 'var(--pixel-info)' },
  DISCARDED: { label: '已弃', color: 'var(--pixel-accent)' },
}

// --- Item Detail Modal ---
const showDetailModal = ref(false)
const detailItem = ref<Item | null>(null)
const detailImages = ref<ItemImage[]>([])
const detailCosts = ref<AdditionalCost[]>([])
const detailLoading = ref(false)

// --- Sub-page Modals ---
const activeModal = ref<'categories' | 'tags' | 'stats' | null>(null)

function openModal(type: 'categories' | 'tags' | 'stats') {
  activeModal.value = type
  if (type === 'stats') {
    reportProgress('REVIEW_STATS').catch(() => {})
  }
}

function closeModal() {
  activeModal.value = null
}

// --- Trash Modal ---
const showTrashModal = ref(false)
const trashItems = ref<Item[]>([])
const trashTotal = ref(0)
const trashPage = ref(1)
const trashPages = ref(1)
const trashLoading = ref(false)

async function openTrashModal() {
  showTrashModal.value = true
  trashPage.value = 1
  await fetchTrashItems()
}

async function fetchTrashItems() {
  trashLoading.value = true
  try {
    const res = await listTrashedItems({ page: trashPage.value, page_size: 20 })
    trashItems.value = res.items || []
    trashTotal.value = res.total
    trashPages.value = res.pages
  } catch {
    notify.error('加载回收站失败')
  } finally {
    trashLoading.value = false
  }
}

async function handleRestore(id: number) {
  try {
    await restoreItem(id)
    notify.success('物品已恢复')
    await fetchTrashItems()
    fetchItems()
    fetchMetadata()
  } catch {
    notify.error('恢复失败')
  }
}

async function handlePermanentDelete(id: number) {
  if (!window.confirm('彻底删除不可恢复，确认？')) return
  try {
    await permanentDeleteItem(id)
    notify.success('物品已彻底删除')
    await fetchTrashItems()
    fetchMetadata()
  } catch {
    notify.error('删除失败')
  }
}

function goToTrashPage(page: number) {
  if (page < 1 || page > trashPages.value) return
  trashPage.value = page
  fetchTrashItems()
}

// --- Create/Edit Item Modal ---
const showCreateModal = ref(false)
const createLoading = ref(false)
const createError = ref('')
const uploadProgress = ref(false)
const newFiles = ref<{ file: File; preview: string }[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const editItemId = ref<number | null>(null)
const existingImages = ref<ItemImage[]>([])
const isEditMode = computed(() => editItemId.value !== null)
const createForm = ref({
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
const createErrors = ref<Record<string, string>>({})

function openCreateModal() {
  editItemId.value = null
  existingImages.value = []
  createForm.value = {
    name: '', description: '', category_id: null,
    purchase_date: '', purchase_price: '', currency: 'CNY',
    purchase_channel: '', current_value: '', warranty_expiry: '',
    expected_lifespan: '', usage_count: '', tag_ids: [],
  }
  createErrors.value = {}
  createError.value = ''
  newFiles.value = []
  showCreateModal.value = true
}

async function openEditModal(id: number) {
  editItemId.value = id
  existingImages.value = []
  createForm.value = {
    name: '', description: '', category_id: null,
    purchase_date: '', purchase_price: '', currency: 'CNY',
    purchase_channel: '', current_value: '', warranty_expiry: '',
    expected_lifespan: '', usage_count: '', tag_ids: [],
  }
  createErrors.value = {}
  createError.value = ''
  newFiles.value = []
  showCreateModal.value = true
  createLoading.value = true
  try {
    const item = await getItem(id)
    createForm.value = {
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
      tag_ids: (item.tags || []).map((t: any) => t.id),
    }
    existingImages.value = (item as any).images || []
  } catch (e: any) {
    createError.value = '加载物品信息失败'
  } finally {
    createLoading.value = false
  }
}

function closeFormModal() {
  showCreateModal.value = false
  newFiles.value.forEach(f => URL.revokeObjectURL(f.preview))
  newFiles.value = []
  editItemId.value = null
  existingImages.value = []
}

function removeExistingImage(imgId: number) {
  deleteImage(imgId).catch(() => {})
  existingImages.value = existingImages.value.filter(img => img.id !== imgId)
}

function validateCreate(): boolean {
  createErrors.value = {}
  if (!createForm.value.name.trim()) createErrors.value.name = '物品名称不能为空'
  if (!createForm.value.purchase_date) createErrors.value.purchase_date = '购买日期不能为空'
  if (!createForm.value.purchase_price || Number(createForm.value.purchase_price) <= 0) {
    createErrors.value.purchase_price = '购买价格必须大于 0'
  }
  return Object.keys(createErrors.value).length === 0
}

function toggleCreateTag(tagId: number) {
  const idx = createForm.value.tag_ids.indexOf(tagId)
  if (idx >= 0) createForm.value.tag_ids.splice(idx, 1)
  else createForm.value.tag_ids.push(tagId)
}

function triggerFileInput() { fileInput.value?.click() }

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files) return
  for (const file of target.files) {
    if (!file.type.startsWith('image/')) continue
    newFiles.value.push({ file, preview: URL.createObjectURL(file) })
  }
  target.value = ''
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  if (!event.dataTransfer?.files) return
  for (const file of event.dataTransfer.files) {
    if (!file.type.startsWith('image/')) continue
    newFiles.value.push({ file, preview: URL.createObjectURL(file) })
  }
}

function removeNewFile(index: number) {
  URL.revokeObjectURL(newFiles.value[index].preview)
  newFiles.value.splice(index, 1)
}

async function handleFormSubmit() {
  if (!validateCreate()) return
  createLoading.value = true
  createError.value = ''
  try {
    const payload: Partial<Item> = {
      name: createForm.value.name.trim(),
      description: createForm.value.description.trim() || null,
      category_id: createForm.value.category_id,
      purchase_date: createForm.value.purchase_date,
      purchase_price: Number(createForm.value.purchase_price),
      currency: createForm.value.currency,
      purchase_channel: createForm.value.purchase_channel.trim() || null,
      current_value: createForm.value.current_value ? Number(createForm.value.current_value) : null,
      warranty_expiry: createForm.value.warranty_expiry || null,
      expected_lifespan: createForm.value.expected_lifespan ? Number(createForm.value.expected_lifespan) : null,
      usage_count: createForm.value.usage_count ? Number(createForm.value.usage_count) : null,
    }
    let saved: Item
    if (isEditMode.value && editItemId.value) {
      saved = await updateItem(editItemId.value, payload)
    } else {
      saved = await createItem(payload)
    }
    if (newFiles.value.length > 0) {
      uploadProgress.value = true
      for (const { file } of newFiles.value) {
        try { await uploadImage(saved.id, file) } catch { /* continue */ }
      }
      uploadProgress.value = false
    }
    const wasEdit = isEditMode.value
    const editId = editItemId.value
    closeFormModal()
    fetchItems()
    fetchMetadata()
    notify.success(wasEdit ? '物品已更新' : '物品已创建')
    if (wasEdit && editId) {
      openItemDetail(editId)
    }
  } catch (e: any) {
    createError.value = e?.data?.detail || '保存失败，请重试'
    notify.error(createError.value)
  } finally {
    createLoading.value = false
    uploadProgress.value = false
  }
}

// --- RPG stat helpers ---
function catPercent(count: number): number {
  const total = overview.value?.total_items ?? 0
  return total > 0 ? Math.round((count / total) * 100) : 0
}

const hoveredCat = ref<number>(-1)
const pieTooltipStyle = ref<Record<string, string>>({})

function onPieHover(index: number, event: MouseEvent) {
  hoveredCat.value = index
  const rect = (event.target as SVGElement).closest('.pie-wrap')?.getBoundingClientRect()
  if (rect) {
    pieTooltipStyle.value = {
      position: 'fixed',
      left: (rect.right + 8) + 'px',
      top: rect.top + 'px',
      zIndex: '400',
    }
  }
}

function onPieLeave() {
  hoveredCat.value = -1
}

const pieColors = [
  '#41A6F6', '#38B764', '#E6AD00', '#E05555', '#9B6ED0',
  '#E08A4A', '#4ECDC4', '#F0C040', '#7B8CDE', '#D46A9E',
]

const pieSegments = computed(() => {
  const total = overview.value?.total_items ?? 0
  if (total === 0 || categoryStats.value.length === 0) return []
  const circumference = 2 * Math.PI * 50
  let accOffset = 0
  return categoryStats.value.map((cat, i) => {
    const fraction = cat.item_count / total
    const dash = `${fraction * circumference} ${circumference}`
    const offset = -accOffset * circumference
    accOffset += fraction
    return {
      color: cat.color || pieColors[i % pieColors.length],
      dash,
      offset,
      name: cat.category_name,
      count: cat.item_count,
      percent: total > 0 ? Math.round((cat.item_count / total) * 100) : 0,
      totalValue: cat.total_value,
      avgDailyCost: cat.avg_daily_cost,
    }
  })
})

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

  const params: ItemListParams = {
    page: currentPage.value,
    page_size: pageSize,
    sort_by: 'created_at',
    order: 'desc',
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

// --- Fetch metadata ---
async function fetchMetadata() {
  try {
    const [cats, tagList, ov, catStats, recent, warranty] = await Promise.all([
      listCategories(), listTags(), getOverview(), getByCategory(),
      getRecentItems(5), getWarrantyAlerts(30),
    ])
    categories.value = cats as Category[]
    tags.value = tagList as Tag[]
    overview.value = ov
    categoryStats.value = catStats as CategoryStat[]
    recentItems.value = recent as RecentItem[]
    warrantyAlerts.value = warranty as WarrantyAlert[]
  } catch {
    // silent fail for metadata
  }
}

// --- Open item detail modal ---
async function openItemDetail(id: number) {
  detailLoading.value = true
  showDetailModal.value = true
  try {
    const res = await getItem(id)
    detailItem.value = res
    detailImages.value = (res as any).images || []
    detailCosts.value = (res as any).additional_costs || []
    reportProgress('VIEW_ITEMS').catch(() => {})
  } catch (e: any) {
    error.value = e?.data?.detail || '加载物品详情失败'
    showDetailModal.value = false
  } finally {
    detailLoading.value = false
  }
}

function closeDetailModal() {
  showDetailModal.value = false
  detailItem.value = null
}

function goEditItem() {
  if (detailItem.value) {
    const id = detailItem.value.id
    closeDetailModal()
    openEditModal(id)
  }
}

function goToAddItem() {
  router.push('/items/new')
}

// --- Reset page when filters change ---
watch([keyword, filterCategory, filterStatus, filterTag], () => {
  currentPage.value = 1
  fetchItems()
})

// --- Pagination ---
function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  fetchItems()
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

// --- Export ---
const exporting = ref(false)
async function handleExport() {
  exporting.value = true
  try {
    const params: ItemListParams = { page: 1, page_size: 20, sort_by: 'created_at', order: 'desc' }
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    if (filterCategory.value !== '') params.category_id = filterCategory.value
    if (filterStatus.value !== '') params.status = filterStatus.value
    if (filterTag.value !== '') params.tag_id = filterTag.value
    await exportItemsCSV(params)
    notify.success('导出成功')
  } catch {
    notify.error('导出失败')
  } finally {
    exporting.value = false
  }
}

// --- Computed for detail modal ---
const totalAdditionalCosts = ref(0)
watch(detailCosts, (costs) => {
  totalAdditionalCosts.value = costs.reduce((sum, c) => sum + c.amount, 0)
})

const dailyDepreciation = ref<number | null>(null)
watch(detailItem, (item) => {
  if (!item || item.current_value == null || item.usage_days <= 0) {
    dailyDepreciation.value = null
    return
  }
  dailyDepreciation.value = (item.purchase_price - item.current_value) / item.usage_days
})

// --- Init ---
onMounted(() => {
  fetchMetadata()
  fetchItems()
})
</script>

<template>
  <div class="inventory-page animate-fade-in">
    <div class="inv-layout">
      <!-- ====== LEFT: Stats Sidebar ====== -->
      <div class="inv-sidebar">
        <!-- Character Portrait -->
        <div class="portrait-card pixel-border">
          <div class="pc-frame">
            <img :src="auth.user?.portrait_url || '/img/portrait.png'" alt="Character" class="pc-img" />
          </div>
          <div class="pc-info">
            <div class="pc-name">冒险者 {{ auth.user?.character_name || auth.user?.username }}</div>
            <div class="pc-level">Lv.{{ overview?.total_items ?? 0 }}</div>
          </div>
        </div>

        <!-- Overview Panel -->
        <div class="sp-card pixel-border">
          <div class="sp-section-header" @click="toggleSection('overview')">
            <span class="sp-icon">◈</span>
            <span>数据概览</span>
            <span class="sp-arrow" :class="{ expanded: expandedSections.overview }">▼</span>
          </div>
          <div v-if="expandedSections.overview" class="sp-body">
            <div class="sp-grid">
              <div class="sp-stat-block">
                <div class="sp-stat-num primary">{{ overview?.total_items ?? 0 }}</div>
                <div class="sp-stat-label">物品总数</div>
              </div>
              <div class="sp-stat-block">
                <div class="sp-stat-num warn">{{ formatCurrency(overview?.total_assets_value ?? 0) }}</div>
                <div class="sp-stat-label">资产总值</div>
              </div>
              <div class="sp-stat-block">
                <div class="sp-stat-num info">{{ formatCurrency(overview?.avg_daily_cost ?? 0) }}</div>
                <div class="sp-stat-label">日均成本</div>
              </div>
              <div class="sp-stat-block">
                <div class="sp-stat-num success">{{ overview?.active_items ?? 0 }}</div>
                <div class="sp-stat-label">活跃物品</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Status Distribution -->
        <div class="sp-card pixel-border">
          <div class="sp-section-header" @click="toggleSection('status')">
            <span class="sp-icon">▣</span>
            <span>状态分布</span>
            <span class="sp-arrow" :class="{ expanded: expandedSections.status }">▼</span>
          </div>
          <div v-if="expandedSections.status" class="sp-body">
            <div class="status-bar-group">
              <div v-for="s in statusList" :key="s.key" class="status-row">
                <div class="status-row-top">
                  <span class="status-dot" :style="{ background: s.color }"></span>
                  <span class="status-label">{{ s.label }}</span>
                  <span class="status-count">{{ s.count }}件</span>
                </div>
                <div class="status-track">
                  <div class="status-fill" :style="{ width: (overview?.total_items ? Math.round(s.count / overview.total_items * 100) : 0) + '%', background: s.color }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Category Pie -->
        <div v-if="categoryStats.length > 0" class="sp-card pixel-border">
          <div class="sp-section-header" @click="toggleSection('category')">
            <span class="sp-icon">▦</span>
            <span>分类占比</span>
            <span class="sp-arrow" :class="{ expanded: expandedSections.category }">▼</span>
          </div>
          <div v-if="expandedSections.category" class="sp-body">
            <div class="pie-wrap" @mouseleave="onPieLeave">
              <svg class="pie-chart" viewBox="0 0 120 120">
                <circle
                  v-for="(seg, i) in pieSegments"
                  :key="i"
                  cx="60" cy="60" r="50"
                  fill="none"
                  :stroke="hoveredCat === i ? seg.color : seg.color + 'cc'"
                  :stroke-width="hoveredCat === i ? 24 : 20"
                  :stroke-dasharray="seg.dash"
                  :stroke-dashoffset="seg.offset"
                  stroke-linecap="butt"
                  class="pie-seg"
                  :class="{ active: hoveredCat === i }"
                  @mouseenter="onPieHover(i, $event)"
                  style="transition: stroke-width 0.15s ease, stroke 0.15s ease; cursor: pointer;"
                />
              </svg>
              <div class="pie-center">
                <template v-if="hoveredCat >= 0 && pieSegments[hoveredCat]">
                  <span class="pie-hover-percent">{{ pieSegments[hoveredCat].percent }}%</span>
                </template>
                <template v-else>
                  <span class="pie-total">{{ overview?.total_items ?? 0 }}</span>
                </template>
              </div>
            </div>
            <div class="pie-legend">
              <div
                v-for="(cat, ci) in categoryStats" :key="cat.category_id ?? 'none'"
                class="legend-item"
                :class="{ active: hoveredCat === ci }"
                @mouseenter="hoveredCat = ci"
                @mouseleave="hoveredCat = -1"
              >
                <span class="legend-dot" :style="{ background: cat.color || pieColors[ci % pieColors.length] }"></span>
                <span class="legend-name">{{ cat.category_name }}</span>
                <span class="legend-val">{{ cat.item_count }}件</span>
              </div>
            </div>
            <!-- Floating tooltip -->
            <Teleport to="body">
              <div
                v-if="hoveredCat >= 0 && pieSegments[hoveredCat]"
                class="pie-tooltip"
                :style="pieTooltipStyle"
              >
                <div class="tt-name" :style="{ color: pieSegments[hoveredCat].color }">{{ pieSegments[hoveredCat].name }}</div>
                <div class="tt-row"><span>数量</span><span>{{ pieSegments[hoveredCat].count }}件 ({{ pieSegments[hoveredCat].percent }}%)</span></div>
                <div class="tt-row"><span>总值</span><span>{{ formatCurrency(pieSegments[hoveredCat].totalValue) }}</span></div>
                <div class="tt-row"><span>日均</span><span>{{ formatCurrency(pieSegments[hoveredCat].avgDailyCost) }}/天</span></div>
              </div>
            </Teleport>
          </div>
        </div>

        <!-- Recent Items -->
        <div v-if="recentItems.length > 0" class="sp-card pixel-border">
          <div class="sp-section-header" @click="toggleSection('recent')">
            <span class="sp-icon">▸</span>
            <span>最近获取</span>
            <span class="sp-badge">{{ recentItems.length }}</span>
            <span class="sp-arrow" :class="{ expanded: expandedSections.recent }">▼</span>
          </div>
          <div v-if="expandedSections.recent" class="sp-body">
            <div class="recent-list">
              <div v-for="ri in recentItems" :key="ri.id" class="recent-item" @click="openItemDetail(ri.id)">
                <div class="ri-name">{{ ri.name }}</div>
                <div class="ri-meta">
                  <span class="ri-cost">{{ formatCurrency(ri.daily_cost) }}/天</span>
                  <span class="ri-date">{{ ri.created_at?.slice(5, 10) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Warranty Alerts -->
        <div v-if="warrantyAlerts.length > 0" class="sp-card pixel-border">
          <div class="sp-section-header alert" @click="toggleSection('warranty')">
            <span class="sp-icon">!</span>
            <span>保修提醒</span>
            <span class="sp-badge warn">{{ warrantyAlerts.length }}</span>
            <span class="sp-arrow" :class="{ expanded: expandedSections.warranty }">▼</span>
          </div>
          <div v-if="expandedSections.warranty" class="sp-body">
            <div class="warranty-list">
              <div v-for="wa in warrantyAlerts" :key="wa.id" class="warranty-item" @click="openItemDetail(wa.id)">
                <div class="wa-name">{{ wa.name }}</div>
                <div class="wa-meta">
                  <span class="wa-days" :class="{ urgent: wa.days_remaining <= 7 }">{{ wa.days_remaining }}天</span>
                  <span class="wa-price">{{ formatCurrency(wa.purchase_price) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ====== RIGHT: Inventory Grid ====== -->
      <div class="inv-main">
        <!-- Top Toolbar: all in one row -->
        <div class="inv-toolbar">
          <div class="toolbar-left">
            <button class="back-btn" @click="router.push('/')">
              <span>◀</span>
              <span>角色信息</span>
            </button>
            <h2 class="inv-title">
              <span class="title-icon">◆</span>
              <span>背包</span>
              <span class="inv-count">{{ totalItems }}件</span>
            </h2>
          </div>
          <div class="toolbar-right">
            <button class="toolbar-btn" @click="openModal('categories')" title="分类管理">▦</button>
            <button class="toolbar-btn" @click="openModal('tags')" title="标签管理">◎</button>
            <button class="toolbar-btn" @click="openModal('stats')" title="数据统计">▤</button>
            <button class="toolbar-btn" :disabled="exporting" @click="handleExport" title="导出CSV">⤓</button>
            <button class="toolbar-btn" @click="openTrashModal" title="回收站">🗑</button>
            <button class="add-item-btn-sm" @click="openCreateModal">+ 添加</button>
          </div>
        </div>
        <div class="inv-filters">
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
          <PixelSelect v-model="filterCategory" :options="categoryOptions" placeholder="全部分类" />
          <PixelSelect v-model="filterStatus" :options="statusOptions" placeholder="全部状态" />
          <PixelSelect v-model="filterTag" :options="tagOptions" placeholder="全部标签" />
        </div>

        <!-- Loading -->
        <div v-if="loading" class="loading-state">
          <div class="pixel-loading"></div>
          <span class="loading-text">加载中...</span>
        </div>

        <!-- Error -->
        <div v-else-if="error" class="error-state">
          <span class="error-icon">!</span>
          <p>{{ error }}</p>
          <button class="retry-btn" @click="fetchItems">重试</button>
        </div>

        <!-- Empty -->
        <div v-else-if="items.length === 0" class="empty-state">
          <span class="empty-icon">▢</span>
          <p class="empty-text">背包是空的</p>
          <button class="add-item-btn-sm" @click="openCreateModal">添加物品</button>
        </div>

        <!-- Inventory Grid -->
        <div v-else class="inv-grid">
          <div
            v-for="item in items"
            :key="item.id"
            class="inv-slot"
            @click="openItemDetail(item.id)"
          >
            <div class="slot-image">
              <img
                v-if="item.images && item.images.length > 0"
                :src="item.images[0].url"
                :alt="item.name"
                class="slot-img"
              />
              <span v-else class="slot-placeholder">◆</span>
            </div>
            <div class="slot-name">{{ item.name }}</div>
            <div class="slot-cost">{{ formatCurrency(item.daily_cost) }}/天</div>
            <span
              class="slot-status"
              :style="{ color: statusMap[item.status]?.color }"
            >●</span>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="!loading && items.length > 0 && totalPages > 1" class="pagination">
          <button
            class="page-btn"
            :disabled="currentPage <= 1"
            @click="goToPage(currentPage - 1)"
          >◀</button>
          <span class="page-info">{{ currentPage }}/{{ totalPages }}</span>
          <button
            class="page-btn"
            :disabled="currentPage >= totalPages"
            @click="goToPage(currentPage + 1)"
          >▶</button>
        </div>
      </div>
    </div>

    <!-- ====== Item Detail Modal ====== -->
    <Teleport to="body">
      <div v-if="showDetailModal" class="modal-overlay" @click.self="closeDetailModal">
        <div class="modal-card">
          <!-- Modal Loading -->
          <div v-if="detailLoading" class="modal-loading">
            <div class="pixel-loading"></div>
          </div>

          <template v-else-if="detailItem">
            <!-- Modal Header -->
            <div class="modal-header">
              <div class="modal-title-row">
                <h2 class="modal-item-name">{{ detailItem.name }}</h2>
                <span
                  class="modal-status"
                  :style="{
                    color: statusMap[detailItem.status]?.color,
                    borderColor: statusMap[detailItem.status]?.color,
                    background: (statusMap[detailItem.status]?.color || '') + '18'
                  }"
                >
                  {{ statusMap[detailItem.status]?.label || detailItem.status }}
                </span>
              </div>
              <button class="modal-close" @click="closeDetailModal">✕</button>
            </div>

            <!-- Modal Body -->
            <div class="modal-body">
              <div class="modal-columns">
                <!-- Left: Image -->
                <div class="modal-left">
                  <div class="modal-image-area">
                    <img
                      v-if="detailImages.length > 0"
                      :src="detailImages[0].url"
                      :alt="detailItem.name"
                      class="modal-image"
                    />
                    <div v-else class="modal-image-placeholder">
                      <span>◆</span>
                    </div>
                  </div>
                </div>

                <!-- Right: Info -->
                <div class="modal-right">
                  <!-- Cost Stats -->
                  <div class="modal-stat-hero">
                    <div class="stat-hero-label">日均成本</div>
                    <div class="stat-hero-value">{{ formatCurrency(detailItem.daily_cost, detailItem.currency) }}</div>
                    <div class="stat-hero-unit">/ 天</div>
                  </div>

                  <div class="modal-detail-grid">
                    <div class="modal-detail-item">
                      <span class="detail-label">购买价格</span>
                      <span class="detail-value highlight">{{ formatCurrency(detailItem.purchase_price, detailItem.currency) }}</span>
                    </div>
                    <div class="modal-detail-item">
                      <span class="detail-label">总投入</span>
                      <span class="detail-value">{{ formatCurrency(detailItem.total_cost, detailItem.currency) }}</span>
                    </div>
                    <div class="modal-detail-item">
                      <span class="detail-label">使用天数</span>
                      <span class="detail-value">{{ formatDays(detailItem.usage_days) }}</span>
                    </div>
                    <div class="modal-detail-item" v-if="detailItem.purchase_channel">
                      <span class="detail-label">购买渠道</span>
                      <span class="detail-value">{{ detailItem.purchase_channel }}</span>
                    </div>
                    <div class="modal-detail-item" v-if="detailItem.current_value != null">
                      <span class="detail-label">当前价值</span>
                      <span class="detail-value">{{ formatCurrency(detailItem.current_value, detailItem.currency) }}</span>
                    </div>
                    <div class="modal-detail-item" v-if="detailItem.description">
                      <span class="detail-label">描述</span>
                      <span class="detail-value desc">{{ detailItem.description }}</span>
                    </div>
                  </div>

                  <!-- Tags -->
                  <div v-if="detailItem.tags && detailItem.tags.length" class="modal-tags">
                    <span
                      v-for="tag in detailItem.tags"
                      :key="tag.id"
                      class="modal-tag"
                      :style="{ borderColor: tag.color || 'var(--pixel-border)' }"
                    >{{ tag.name }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Modal Actions -->
            <div class="modal-actions">
              <button class="pixel-btn primary" @click="goEditItem">
                ✎ 编辑
              </button>
              <button class="pixel-btn" @click="closeDetailModal">
                关闭
              </button>
            </div>
          </template>
        </div>
      </div>
    </Teleport>

    <!-- ====== Categories Modal ====== -->
    <Teleport to="body">
      <div v-if="activeModal === 'categories'" class="sub-modal-overlay" @click.self="closeModal">
        <div class="sub-modal">
          <div class="sub-modal-header">
            <h3><span class="sub-modal-icon">▦</span> 分类管理</h3>
            <button class="sub-modal-close" @click="closeModal">✕</button>
          </div>
          <div class="sub-modal-body">
            <Categories />
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ====== Tags Modal ====== -->
    <Teleport to="body">
      <div v-if="activeModal === 'tags'" class="sub-modal-overlay" @click.self="closeModal">
        <div class="sub-modal">
          <div class="sub-modal-header">
            <h3><span class="sub-modal-icon">◎</span> 标签管理</h3>
            <button class="sub-modal-close" @click="closeModal">✕</button>
          </div>
          <div class="sub-modal-body">
            <Tags />
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ====== Stats Modal ====== -->
    <Teleport to="body">
      <div v-if="activeModal === 'stats'" class="sub-modal-overlay" @click.self="closeModal">
        <div class="sub-modal stats-modal">
          <div class="sub-modal-header">
            <h3><span class="sub-modal-icon">▤</span> 数据统计</h3>
            <button class="sub-modal-close" @click="closeModal">✕</button>
          </div>
          <div class="sub-modal-body">
            <Stats />
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ====== Trash Modal ====== -->
    <Teleport to="body">
      <div v-if="showTrashModal" class="sub-modal-overlay" @click.self="showTrashModal = false">
        <div class="sub-modal trash-modal">
          <div class="sub-modal-header">
            <h3><span class="sub-modal-icon">🗑</span> 回收站 <span class="trash-count">({{ trashTotal }}件)</span></h3>
            <button class="sub-modal-close" @click="showTrashModal = false">✕</button>
          </div>
          <div class="sub-modal-body">
            <div v-if="trashLoading" class="cf-loading">
              <div class="pixel-loading"></div>
              <span>加载中...</span>
            </div>
            <div v-else-if="trashItems.length === 0" class="trash-empty">
              <span class="trash-empty-icon">▢</span>
              <span>回收站是空的</span>
            </div>
            <div v-else class="trash-grid">
              <div v-for="item in trashItems" :key="item.id" class="trash-item">
                <div class="trash-item-left">
                  <span class="trash-item-name">{{ item.name }}</span>
                  <span class="trash-item-date">删除于 {{ item.deleted_at?.slice(0, 10) }}</span>
                </div>
                <div class="trash-item-actions">
                  <button class="trash-btn restore" @click="handleRestore(item.id)" title="恢复">⟲ 恢复</button>
                  <button class="trash-btn danger" @click="handlePermanentDelete(item.id)" title="彻底删除">✕ 彻底</button>
                </div>
              </div>
            </div>
            <div v-if="trashPages > 1" class="pagination">
              <button class="page-btn" :disabled="trashPage <= 1" @click="goToTrashPage(trashPage - 1)">◀</button>
              <span class="page-info">{{ trashPage }}/{{ trashPages }}</span>
              <button class="page-btn" :disabled="trashPage >= trashPages" @click="goToTrashPage(trashPage + 1)">▶</button>
            </div>
            <div class="trash-warning">⚠ 彻底删除不可恢复</div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ====== Create/Edit Item Modal ====== -->
    <Teleport to="body">
      <div v-if="showCreateModal" class="sub-modal-overlay" @click.self="closeFormModal">
        <div class="sub-modal create-modal">
          <div class="sub-modal-header">
            <h3>
              <span class="sub-modal-icon">{{ isEditMode ? '✎' : '▶' }}</span>
              {{ isEditMode ? '编辑物品' : '新增物品' }}
            </h3>
            <button class="sub-modal-close" @click="closeFormModal">✕</button>
          </div>
          <div class="sub-modal-body">
            <div v-if="createLoading && isEditMode" class="cf-loading">
              <div class="pixel-loading"></div>
              <span>加载中...</span>
            </div>
            <template v-else>
              <div v-if="createError" class="cf-error">
                <span>!</span> {{ createError }}
              </div>
              <form class="cf-form" @submit.prevent="handleFormSubmit">
              <!-- Basic Info -->
              <div class="cf-section">
                <h4 class="cf-section-title">— 基本信息 —</h4>
                <div class="cf-field">
                  <label class="cf-label"><span class="cf-bracket">[</span>名称<span class="cf-bracket">]</span> *</label>
                  <input v-model="createForm.name" type="text" class="pixel-input" placeholder="输入物品名称..." maxlength="100" />
                  <span v-if="createErrors.name" class="cf-err">{{ createErrors.name }}</span>
                </div>
                <div class="cf-field">
                  <label class="cf-label"><span class="cf-bracket">[</span>描述<span class="cf-bracket">]</span></label>
                  <textarea v-model="createForm.description" class="pixel-input cf-textarea" placeholder="物品描述（可选）..." rows="2"></textarea>
                </div>
                <div class="cf-field">
                  <label class="cf-label"><span class="cf-bracket">[</span>分类<span class="cf-bracket">]</span></label>
                  <PixelSelect v-model="createForm.category_id" :options="categoryOptions" placeholder="— 选择分类 —" />
                </div>
              </div>

              <!-- Purchase Info -->
              <div class="cf-section">
                <h4 class="cf-section-title">— 购买信息 —</h4>
                <div class="cf-field">
                  <label class="cf-label"><span class="cf-bracket">[</span>购买日期<span class="cf-bracket">]</span> *</label>
                  <PixelDatePicker v-model="createForm.purchase_date" placeholder="选择购买日期" />
                  <span v-if="createErrors.purchase_date" class="cf-err">{{ createErrors.purchase_date }}</span>
                </div>
                <div class="cf-inline">
                  <div class="cf-field cf-grow">
                    <label class="cf-label"><span class="cf-bracket">[</span>价格<span class="cf-bracket">]</span> *</label>
                    <input v-model="createForm.purchase_price" type="number" class="pixel-input" placeholder="0.00" step="0.01" min="0" />
                    <span v-if="createErrors.purchase_price" class="cf-err">{{ createErrors.purchase_price }}</span>
                  </div>
                  <div class="cf-field cf-currency">
                    <label class="cf-label"><span class="cf-bracket">[</span>币种<span class="cf-bracket">]</span></label>
                    <PixelSelect v-model="createForm.currency" :options="currencyOptions" />
                  </div>
                </div>
                <div class="cf-field">
                  <label class="cf-label"><span class="cf-bracket">[</span>购买渠道<span class="cf-bracket">]</span></label>
                  <input v-model="createForm.purchase_channel" type="text" class="pixel-input" placeholder="购买渠道（可选）..." maxlength="100" />
                </div>
              </div>

              <!-- Extra Info -->
              <div class="cf-section">
                <h4 class="cf-section-title">— 附加信息 —</h4>
                <div class="cf-inline">
                  <div class="cf-field cf-grow">
                    <label class="cf-label"><span class="cf-bracket">[</span>当前价值<span class="cf-bracket">]</span></label>
                    <input v-model="createForm.current_value" type="number" class="pixel-input" placeholder="当前价值" step="0.01" min="0" />
                  </div>
                  <div class="cf-field cf-grow">
                    <label class="cf-label"><span class="cf-bracket">[</span>使用次数<span class="cf-bracket">]</span></label>
                    <input v-model="createForm.usage_count" type="number" class="pixel-input" placeholder="使用次数" min="0" />
                  </div>
                </div>
                <div class="cf-inline">
                  <div class="cf-field cf-grow">
                    <label class="cf-label"><span class="cf-bracket">[</span>保修到期<span class="cf-bracket">]</span></label>
                    <PixelDatePicker v-model="createForm.warranty_expiry" placeholder="选择保修到期日" />
                  </div>
                  <div class="cf-field cf-grow">
                    <label class="cf-label"><span class="cf-bracket">[</span>预期寿命(天)<span class="cf-bracket">]</span></label>
                    <input v-model="createForm.expected_lifespan" type="number" class="pixel-input" placeholder="预期寿命" min="0" />
                  </div>
                </div>
              </div>

              <!-- Tags -->
              <div class="cf-section">
                <h4 class="cf-section-title">— 标签 —</h4>
                <div v-if="tags.length === 0" class="cf-hint">暂无标签</div>
                <div v-else class="cf-tags">
                  <label
                    v-for="tag in tags" :key="tag.id"
                    class="cf-tag"
                    :class="{ active: createForm.tag_ids.includes(tag.id) }"
                  >
                    <input type="checkbox" :checked="createForm.tag_ids.includes(tag.id)" class="cf-tag-hidden" @change="toggleCreateTag(tag.id)" />
                    <span class="cf-tag-box">■</span>
                    <span>{{ tag.name }}</span>
                  </label>
                </div>
              </div>

              <!-- Images -->
              <div class="cf-section">
                <h4 class="cf-section-title">— 图片 —</h4>
                <div v-if="existingImages.length > 0" class="cf-images">
                  <div v-for="img in existingImages" :key="img.id" class="cf-img-thumb">
                    <img :src="img.url" :alt="'Image ' + img.id" />
                    <button type="button" class="cf-img-del" @click="removeExistingImage(img.id)">✕</button>
                  </div>
                </div>
                <div v-if="newFiles.length > 0" class="cf-images">
                  <div v-for="(f, i) in newFiles" :key="i" class="cf-img-thumb">
                    <img :src="f.preview" :alt="'New ' + (i + 1)" />
                    <button type="button" class="cf-img-del" @click="removeNewFile(i)">✕</button>
                  </div>
                </div>
                <div class="cf-upload" @click="triggerFileInput" @drop="handleDrop" @dragover.prevent>
                  <template v-if="!uploadProgress">
                    <span class="cf-upload-icon">↑</span>
                    <span class="cf-upload-text">拖拽图片或点击选择</span>
                  </template>
                  <div v-else class="pixel-loading"></div>
                </div>
                <input ref="fileInput" type="file" accept="image/*" multiple style="display:none" @change="handleFileSelect" />
              </div>

              <!-- Actions -->
              <div class="cf-actions">
                <button type="submit" class="pixel-btn primary" :disabled="createLoading">
                  <span v-if="createLoading" class="pixel-loading inline"></span>
                  <span v-else>{{ isEditMode ? '✎ 保存' : '▶ 保存' }}</span>
                </button>
                <button type="button" class="pixel-btn" @click="closeFormModal">取消</button>
              </div>
            </form>
            </template>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.inventory-page {
  min-height: 100%;
}

/* ===== Main Layout ===== */
.inv-layout {
  display: grid;
  grid-template-columns: 1fr 3fr;
  gap: 20px;
  align-items: start;
}

/* ===== Left Sidebar ===== */
.inv-sidebar {
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: sticky;
  top: 0;
  overflow-y: auto;
  max-height: calc(100vh - 100px);
}

/* Portrait Card */
.portrait-card {
  background: var(--pixel-card-bg);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
}

.pc-frame {
  width: 60px;
  height: 78px;
  border: 2px solid var(--pixel-primary);
  background: var(--pixel-bg);
  overflow: hidden;
  flex-shrink: 0;
}

.pc-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  image-rendering: pixelated;
}

.pc-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pc-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  font-weight: 700;
  color: var(--pixel-primary);
}

.pc-level {
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  color: var(--pixel-warning);
  letter-spacing: 0.5px;
}

/* Sidebar Panel Card */
.sp-card {
  background: var(--pixel-card-bg);
}

.sp-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-text);
  border-bottom: 2px solid var(--pixel-border);
  user-select: none;
  transition: background 0.1s ease;
}

.sp-section-header:hover {
  background: rgba(65, 166, 246, 0.04);
}

.sp-section-header.alert {
  color: var(--pixel-warning);
}

.sp-icon {
  font-size: 14px;
  color: var(--pixel-primary);
  width: 18px;
  text-align: center;
}

.sp-section-header.alert .sp-icon {
  color: var(--pixel-warning);
}

.sp-arrow {
  margin-left: auto;
  font-size: 8px;
  color: var(--pixel-text-secondary);
  transition: transform 0.2s ease;
}

.sp-arrow.expanded {
  transform: rotate(180deg);
}

.sp-badge {
  margin-left: auto;
  font-size: 10px;
  padding: 1px 6px;
  border: 2px solid var(--pixel-primary);
  color: var(--pixel-primary);
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
}

.sp-badge.warn {
  border-color: var(--pixel-warning);
  color: var(--pixel-warning);
}

.sp-body {
  padding: 10px 12px;
}

/* Stat Grid */
.sp-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.sp-stat-block {
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sp-stat-num {
  font-family: 'Press Start 2P', monospace;
  font-size: 11px;
  font-weight: 700;
}
.sp-stat-num.primary { color: var(--pixel-primary); text-shadow: 0 0 6px rgba(65,166,246,0.2); }
.sp-stat-num.warn { color: var(--pixel-warning); }
.sp-stat-num.info { color: var(--pixel-info); }
.sp-stat-num.success { color: var(--pixel-success); }

.sp-stat-label {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

/* Status Distribution */
.status-bar-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-row {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.status-row-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  flex-shrink: 0;
}

.status-label {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text);
  flex: 1;
}

.status-count {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

.status-track {
  height: 8px;
  background: var(--pixel-bg);
  border: 1px solid var(--pixel-border);
  overflow: hidden;
}

.status-fill {
  height: 100%;
  transition: width 0.4s ease-out;
}

/* Pie Chart */
.pie-wrap {
  position: relative;
  width: 130px;
  height: 130px;
  margin: 0 auto;
}

.pie-chart {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.pie-seg.active {
  filter: drop-shadow(0 0 4px currentColor);
}

.pie-center {
  position: absolute;
  inset: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--pixel-card-bg);
  border-radius: 50%;
  pointer-events: none;
}

.pie-total {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  color: var(--pixel-primary);
}

.pie-hover-percent {
  font-family: 'Press Start 2P', monospace;
  font-size: 12px;
  color: var(--pixel-text);
}

/* Pie Tooltip (Teleported to body) */
.pie-tooltip {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-primary);
  padding: 10px 12px;
  box-shadow: 4px 4px 0 var(--pixel-shadow);
  min-width: 160px;
  animation: tt-in 0.1s ease-out;
  pointer-events: none;
}

@keyframes tt-in {
  from { opacity: 0; transform: translateX(-4px); }
  to { opacity: 1; transform: translateX(0); }
}

.tt-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--pixel-border);
}

.tt-row {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
  line-height: 1.8;
}

.tt-row span:last-child { color: var(--pixel-text); }

/* Legend */
.pie-legend {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 4px;
  cursor: pointer;
  transition: background 0.1s ease;
}

.legend-item:hover,
.legend-item.active {
  background: rgba(65, 166, 246, 0.08);
}

.legend-dot {
  width: 8px;
  height: 8px;
  flex-shrink: 0;
  border: 1px solid rgba(255,255,255,0.15);
}

.legend-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.legend-val {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 10px;
  color: var(--pixel-text-secondary);
  flex-shrink: 0;
}

/* Recent Items */
.recent-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.recent-item {
  padding: 6px 8px;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  cursor: pointer;
  transition: border-color 0.1s ease;
}

.recent-item:hover {
  border-color: var(--pixel-primary);
}

.ri-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ri-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 3px;
}

.ri-cost {
  font-size: 10px;
  color: var(--pixel-primary);
}

.ri-date {
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

/* Warranty Alerts */
.warranty-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.warranty-item {
  padding: 6px 8px;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-warning);
  cursor: pointer;
  transition: background 0.1s ease;
}

.warranty-item:hover {
  background: rgba(230, 173, 0, 0.06);
}

.wa-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wa-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 3px;
}

.wa-days {
  font-size: 10px;
  color: var(--pixel-warning);
}

.wa-days.urgent {
  color: var(--pixel-accent);
  font-weight: 700;
}

.wa-price {
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

/* Search */
.search-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
  font-size: 14px;
  color: var(--pixel-text-secondary);
  pointer-events: none;
  z-index: 1;
}

.search-input {
  padding-left: 30px !important;
}

/* ===== Toolbar ===== */
.inv-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-btn {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  font-size: 16px;
  cursor: pointer;
  transition: border-color 0.12s ease, color 0.12s ease, background 0.12s ease;
}

.toolbar-btn:hover {
  border-color: var(--pixel-primary);
  color: var(--pixel-primary);
  background: rgba(65, 166, 246, 0.06);
}

.toolbar-btn:active {
  transform: translate(1px, 1px);
}

/* ===== Filters Row ===== */
.inv-filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.inv-filters .search-wrap {
  flex: 1;
  min-width: 160px;
}

.inv-filters .px-select {
  min-width: 110px;
  flex-shrink: 0;
}

/* Shared Input */
.pixel-input {
  background: var(--pixel-bg);
  border: 3px solid var(--pixel-border);
  color: var(--pixel-text);
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  padding: 8px 10px;
  outline: none;
  width: 100%;
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

/* Add Button (small, in header) */
.add-item-btn-sm {
  background: var(--pixel-primary);
  border: 3px solid var(--pixel-primary);
  color: var(--pixel-bg);
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  padding: 6px 14px;
  cursor: pointer;
  box-shadow: 2px 2px 0 var(--pixel-shadow);
  white-space: nowrap;
  transition: transform 0.08s ease, box-shadow 0.15s ease;
}

.add-item-btn-sm:hover {
  box-shadow: 2px 2px 0 var(--pixel-shadow), 0 0 6px rgba(65, 166, 246, 0.3);
}

.add-item-btn-sm:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

/* ===== Right: Inventory Main ===== */
.inv-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  padding: 6px 12px;
  cursor: pointer;
  box-shadow: 2px 2px 0 var(--pixel-shadow);
  transition: border-color 0.12s ease, color 0.12s ease;
  white-space: nowrap;
}

.back-btn:hover {
  border-color: var(--pixel-primary);
  color: var(--pixel-primary);
}

.back-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

.inv-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 14px;
  color: var(--pixel-primary);
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
}

.title-icon {
  font-size: 18px;
}

.inv-count {
  font-size: 8px;
  color: var(--pixel-text-secondary);
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
}

/* Loading / Error / Empty */
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
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
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
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  padding: 6px 16px;
  cursor: pointer;
}

.retry-btn:hover {
  background: var(--pixel-accent);
  color: var(--pixel-bg);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 0;
  gap: 16px;
}

.empty-icon {
  font-size: 64px;
  color: var(--pixel-border);
  animation: pixel-float 3s ease-in-out infinite;
}

.empty-text {
  font-family: 'Press Start 2P', monospace;
  font-size: 11px;
  color: var(--pixel-text-secondary);
}

/* ===== Inventory Grid ===== */
.inv-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 12px;
}

.inv-slot {
  aspect-ratio: 3/4;
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px;
  cursor: pointer;
  position: relative;
  transition: border-color 0.12s ease, transform 0.08s ease, box-shadow 0.15s ease;
  will-change: transform;
}

.inv-slot:hover {
  border-color: var(--pixel-primary);
  box-shadow: 2px 2px 0 var(--pixel-shadow), 0 0 6px rgba(65, 166, 246, 0.15);
}

.inv-slot:active {
  transform: translate(2px, 2px);
}

/* Slot content */
.slot-image {
  width: 100%;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
}

.slot-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.slot-placeholder {
  font-size: 28px;
  color: var(--pixel-border);
}

.slot-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 10px;
  color: var(--pixel-text);
  text-align: center;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.slot-cost {
  font-size: 8px;
  color: var(--pixel-primary);
  white-space: nowrap;
}

.slot-status {
  position: absolute;
  top: 4px;
  right: 4px;
  font-size: 10px;
}

/* ===== Pagination ===== */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px 0;
  border-top: 2px solid var(--pixel-border);
}

.page-btn {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  color: var(--pixel-text);
  font-size: 14px;
  padding: 6px 12px;
  cursor: pointer;
  box-shadow: 2px 2px 0 var(--pixel-shadow);
}

.page-btn:hover:not(:disabled) {
  border-color: var(--pixel-primary);
  color: var(--pixel-primary);
}

.page-btn:active:not(:disabled) {
  transform: translate(1px, 1px);
}

.page-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.page-info {
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  color: var(--pixel-text-secondary);
}

/* ===== Item Detail Modal ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  animation: pixel-fade-in 0.15s ease-out;
}

.modal-card {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  box-shadow: 6px 6px 0 var(--pixel-shadow);
  width: 680px;
  max-width: 92vw;
  max-height: 90vh;
  overflow-y: auto;
  animation: pixel-scale-in 0.2s ease-out;
}

.modal-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px;
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 3px solid var(--pixel-border);
  background: var(--pixel-bg-secondary);
}

.modal-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.modal-item-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 16px;
  font-weight: 700;
  color: var(--pixel-primary);
  margin: 0;
}

.modal-status {
  font-size: 10px;
  padding: 2px 8px;
  border: 2px solid;
  white-space: nowrap;
}

.modal-close {
  background: none;
  border: 2px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  font-size: 16px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  flex-shrink: 0;
}

.modal-close:hover {
  border-color: var(--pixel-accent);
  color: var(--pixel-accent);
}

.modal-body {
  padding: 20px;
}

.modal-columns {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 20px;
}

.modal-image-area {
  width: 100%;
  aspect-ratio: 1;
  background: var(--pixel-bg);
  border: 3px solid var(--pixel-border);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.modal-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.modal-image-placeholder {
  font-size: 48px;
  color: var(--pixel-border);
}

/* Stat Hero */
.modal-stat-hero {
  text-align: center;
  padding: 8px 0 12px;
}

.stat-hero-label {
  font-size: 10px;
  color: var(--pixel-text-secondary);
  margin-bottom: 4px;
}

.stat-hero-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--pixel-primary);
  text-shadow: 0 0 10px rgba(65, 166, 246, 0.3);
}

.stat-hero-unit {
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

/* Detail Grid */
.modal-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 2px solid var(--pixel-border);
}

.modal-detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.modal-detail-item:has(.desc) {
  grid-column: 1 / -1;
}

.detail-label {
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

.detail-value {
  font-size: 13px;
  color: var(--pixel-text);
}

.detail-value.highlight {
  color: var(--pixel-primary);
  font-weight: 600;
}

.detail-value.desc {
  line-height: 1.5;
  white-space: pre-wrap;
}

/* Tags */
.modal-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.modal-tag {
  font-size: 10px;
  padding: 2px 8px;
  border: 2px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  background: var(--pixel-bg);
}

/* Modal Actions */
.modal-actions {
  display: flex;
  gap: 8px;
  padding: 16px 20px;
  border-top: 3px solid var(--pixel-border);
  justify-content: flex-end;
}

.pixel-btn {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  padding: 8px 16px;
  border: 3px solid var(--pixel-border);
  background: var(--pixel-bg);
  color: var(--pixel-text);
  cursor: pointer;
  box-shadow: 3px 3px 0 var(--pixel-shadow);
  transition: transform 0.08s ease, box-shadow 0.15s ease;
}

.pixel-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

.pixel-btn.primary {
  background: var(--pixel-primary);
  border-color: var(--pixel-primary);
  color: var(--pixel-bg);
}

.pixel-btn.primary:hover {
  box-shadow: 3px 3px 0 var(--pixel-shadow), 0 0 6px rgba(65, 166, 246, 0.3);
}

/* ===== Responsive ===== */
@media (max-width: 900px) {
  .inv-layout {
    grid-template-columns: 1fr;
  }

  .sub-modal,
  .sub-modal.stats-modal {
    width: 96vw;
    max-height: 90vh;
  }

  .inv-sidebar {
    position: static;
    max-height: none;
  }

  .modal-columns {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .inv-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 900px) and (min-width: 641px) {
  .inv-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

/* ===== Sub-page Modals ===== */
.sub-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  animation: pixel-fade-in 0.15s ease-out;
}

.sub-modal {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  box-shadow: 6px 6px 0 var(--pixel-shadow);
  width: 800px;
  max-width: 92vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  animation: pixel-scale-in 0.2s ease-out;
}

.sub-modal.stats-modal {
  width: 1100px;
}

.sub-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--pixel-bg-secondary);
  border-bottom: 3px solid var(--pixel-border);
  flex-shrink: 0;
}

.sub-modal-header h3 {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 13px;
  color: var(--pixel-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.sub-modal-icon {
  font-size: 16px;
}

.sub-modal-close {
  background: none;
  border: 2px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  font-size: 16px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  flex-shrink: 0;
}

.sub-modal-close:hover {
  border-color: var(--pixel-accent);
  color: var(--pixel-accent);
}

.sub-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

/* ===== Create Item Form (in modal) ===== */
.trash-modal {
  width: 600px;
}

.trash-count {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

.trash-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px 0;
  color: var(--pixel-text-secondary);
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
}

.trash-empty-icon {
  font-size: 36px;
  color: var(--pixel-border);
}

.trash-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.trash-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
}

.trash-item-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.trash-item-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trash-item-date {
  font-size: 10px;
  color: var(--pixel-text-secondary);
}

.trash-item-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.trash-btn {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 10px;
  padding: 4px 10px;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-card-bg);
  color: var(--pixel-text-secondary);
  cursor: pointer;
  transition: border-color 0.1s, color 0.1s;
  white-space: nowrap;
}

.trash-btn.restore:hover {
  border-color: var(--pixel-success);
  color: var(--pixel-success);
}

.trash-btn.danger:hover {
  border-color: var(--pixel-accent);
  color: var(--pixel-accent);
}

.trash-warning {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 2px solid var(--pixel-border);
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 10px;
  color: var(--pixel-warning);
  text-align: center;
}

/* ===== Create Item Form (in modal) ===== */
.create-modal {
  width: 640px;
}

.cf-error {
  background: rgba(255, 107, 107, 0.1);
  border: 2px solid var(--pixel-accent);
  color: var(--pixel-accent);
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.cf-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px 0;
  color: var(--pixel-text-secondary);
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
}

.cf-form {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cf-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 14px;
  border-bottom: 2px dashed var(--pixel-border);
  margin-bottom: 10px;
}

.cf-section:last-of-type {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.cf-section-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  color: var(--pixel-text-secondary);
  letter-spacing: 1px;
  margin: 0;
}

.cf-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cf-label {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  color: var(--pixel-text-secondary);
  letter-spacing: 1px;
}

.cf-bracket { color: var(--pixel-border); }
.cf-err { font-family: var(--font-pixel), 'Ark Pixel', monospace; font-size: 11px; color: var(--pixel-accent); }

.cf-textarea { resize: vertical; min-height: 48px; line-height: 1.4; }

.cf-inline { display: flex; gap: 10px; }
.cf-grow { flex: 1; min-width: 0; }
.cf-currency { min-width: 110px; flex: 0 0 110px; }

.cf-hint { font-family: var(--font-pixel), 'Ark Pixel', monospace; font-size: 12px; color: var(--pixel-text-secondary); opacity: 0.6; }

.cf-tags { display: flex; flex-wrap: wrap; gap: 6px; }

.cf-tag {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 8px;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
  cursor: pointer;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-text-secondary);
  user-select: none;
  transition: border-color 0.12s, background 0.12s, color 0.12s;
}
.cf-tag:hover { border-color: var(--pixel-primary); }
.cf-tag.active { border-color: var(--pixel-primary); background: rgba(65,166,246,0.1); color: var(--pixel-primary); }
.cf-tag-hidden { position: absolute; opacity: 0; width: 0; height: 0; pointer-events: none; }
.cf-tag-box { font-size: 9px; color: var(--pixel-border); }
.cf-tag.active .cf-tag-box { color: var(--pixel-primary); }

.cf-images { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.cf-img-thumb { position: relative; width: 64px; height: 64px; border: 2px solid var(--pixel-border); overflow: hidden; }
.cf-img-thumb img { width: 100%; height: 100%; object-fit: cover; }
.cf-img-del {
  position: absolute; top: 0; right: 0; width: 18px; height: 18px;
  background: var(--pixel-accent); color: var(--pixel-bg); border: none;
  font-size: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 0;
}
.cf-img-del:hover { background: #ff4040; }

.cf-upload {
  border: 3px dashed var(--pixel-border);
  padding: 20px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: border-color 0.12s, background 0.12s;
}
.cf-upload:hover { border-color: var(--pixel-primary); background: rgba(65,166,246,0.04); }
.cf-upload-icon { font-size: 20px; color: var(--pixel-text-secondary); }
.cf-upload-text { font-family: var(--font-pixel), 'Ark Pixel', monospace; font-size: 11px; color: var(--pixel-text-secondary); margin: 0; }

.cf-actions { display: flex; gap: 10px; padding-top: 14px; }
.cf-actions .pixel-loading.inline { display: inline-block; width: 14px; height: 14px; border-width: 2px; }
</style>
