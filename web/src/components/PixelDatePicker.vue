<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
  width?: string
}>(), {
  placeholder: '选择日期',
  width: 'auto',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const open = ref(false)
const triggerRef = ref<HTMLElement | null>(null)
const panelRef = ref<HTMLElement | null>(null)

const weekDays = ['日', '一', '二', '三', '四', '五', '六']

const today = new Date()
const viewYear = ref(today.getFullYear())
const viewMonth = ref(today.getMonth())

const displayText = computed(() => {
  if (!props.modelValue) return ''
  return props.modelValue
})

const displayMonth = computed(() => `${viewYear.value}年${viewMonth.value + 1}月`)

const calendarDays = computed(() => {
  const y = viewYear.value
  const m = viewMonth.value
  const firstDay = new Date(y, m, 1).getDay()
  const daysInMonth = new Date(y, m + 1, 0).getDate()
  const prevDays = new Date(y, m, 0).getDate()

  const days: { date: string; day: number; inMonth: boolean; isToday: boolean; selected: boolean }[] = []

  for (let i = firstDay - 1; i >= 0; i--) {
    const d = prevDays - i
    const pm = m === 0 ? 11 : m - 1
    const py = m === 0 ? y - 1 : y
    days.push({ date: formatStr(py, pm, d), day: d, inMonth: false, isToday: false, selected: false })
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = formatStr(y, m, d)
    days.push({
      date: dateStr,
      day: d,
      inMonth: true,
      isToday: dateStr === formatToday(),
      selected: dateStr === props.modelValue,
    })
  }

  const remaining = 42 - days.length
  for (let d = 1; d <= remaining; d++) {
    const nm = m === 11 ? 0 : m + 1
    const ny = m === 11 ? y + 1 : y
    days.push({ date: formatStr(ny, nm, d), day: d, inMonth: false, isToday: false, selected: false })
  }

  return days
})

function formatStr(y: number, m: number, d: number): string {
  return `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

function formatToday(): string {
  const t = new Date()
  return formatStr(t.getFullYear(), t.getMonth(), t.getDate())
}

function toggle() {
  open.value = !open.value
  if (open.value && props.modelValue) {
    const [y, m] = props.modelValue.split('-').map(Number)
    if (y && m) {
      viewYear.value = y
      viewMonth.value = m - 1
    }
  }
}

function selectDate(date: string) {
  emit('update:modelValue', date)
  open.value = false
}

function clearDate() {
  emit('update:modelValue', '')
  open.value = false
}

function prevMonth() {
  if (viewMonth.value === 0) {
    viewMonth.value = 11
    viewYear.value--
  } else {
    viewMonth.value--
  }
}

function nextMonth() {
  if (viewMonth.value === 11) {
    viewMonth.value = 0
    viewYear.value++
  } else {
    viewMonth.value++
  }
}

function goToday() {
  const t = new Date()
  viewYear.value = t.getFullYear()
  viewMonth.value = t.getMonth()
}

function onClickOutside(e: MouseEvent) {
  if (!open.value) return
  const target = e.target as HTMLElement
  if (triggerRef.value?.contains(target) || panelRef.value?.contains(target)) return
  open.value = false
}

onMounted(() => document.addEventListener('click', onClickOutside, true))
onBeforeUnmount(() => document.removeEventListener('click', onClickOutside, true))
</script>

<template>
  <div class="px-datepicker" :style="{ width }">
    <div
      ref="triggerRef"
      class="px-date-trigger"
      :class="{ active: open }"
      @click="toggle"
    >
      <span class="px-date-text" :class="{ placeholder: !modelValue }">
        {{ displayText || placeholder }}
      </span>
      <span class="px-date-icon">📅</span>
    </div>
    <div v-if="open" ref="panelRef" class="px-date-panel">
      <div class="px-date-nav">
        <button class="px-nav-btn" @click="prevMonth">◀</button>
        <span class="px-month-label">{{ displayMonth }}</span>
        <button class="px-nav-btn" @click="nextMonth">▶</button>
      </div>
      <div class="px-week-header">
        <span v-for="d in weekDays" :key="d" class="px-week-day">{{ d }}</span>
      </div>
      <div class="px-days-grid">
        <div
          v-for="(d, i) in calendarDays"
          :key="i"
          class="px-day"
          :class="{ outside: !d.inMonth, today: d.isToday, selected: d.selected }"
          @click="selectDate(d.date)"
        >{{ d.day }}</div>
      </div>
      <div class="px-date-footer">
        <button class="px-footer-btn" @click="goToday">今天</button>
        <button class="px-footer-btn clear" @click="clearDate">清除</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.px-datepicker {
  position: relative;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
}

.px-date-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  background: var(--pixel-bg);
  border: 3px solid var(--pixel-border);
  color: var(--pixel-text);
  padding: 8px 10px;
  cursor: pointer;
  user-select: none;
  transition: border-color 0.12s ease;
}

.px-date-trigger:hover {
  border-color: var(--pixel-primary);
}

.px-date-trigger.active {
  border-color: var(--pixel-primary);
  box-shadow: 0 0 0 1px var(--pixel-primary);
}

.px-date-text {
  flex: 1;
  letter-spacing: 0.5px;
}

.px-date-text.placeholder {
  color: var(--pixel-text-secondary);
  opacity: 0.5;
}

.px-date-icon {
  font-size: 12px;
  flex-shrink: 0;
}

.px-date-panel {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 300;
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-primary);
  border-top: none;
  width: 260px;
  padding: 8px;
  animation: px-date-in 0.1s ease-out;
  box-shadow: 4px 4px 0 var(--pixel-shadow);
}

@keyframes px-date-in {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Navigation */
.px-date-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0 8px;
}

.px-nav-btn {
  background: none;
  border: 2px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  font-size: 10px;
  padding: 2px 8px;
  cursor: pointer;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  transition: border-color 0.1s, color 0.1s;
}

.px-nav-btn:hover {
  border-color: var(--pixel-primary);
  color: var(--pixel-primary);
}

.px-month-label {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-text);
  font-weight: 600;
}

/* Week header */
.px-week-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0;
  margin-bottom: 4px;
}

.px-week-day {
  text-align: center;
  font-size: 10px;
  color: var(--pixel-text-secondary);
  padding: 4px 0;
}

/* Days grid */
.px-days-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.px-day {
  text-align: center;
  padding: 5px 0;
  cursor: pointer;
  font-size: 12px;
  color: var(--pixel-text);
  border: 1px solid transparent;
  transition: background 0.08s, color 0.08s, border-color 0.08s;
}

.px-day:hover {
  background: rgba(65, 166, 246, 0.1);
  border-color: var(--pixel-primary);
}

.px-day.outside {
  color: var(--pixel-text-secondary);
  opacity: 0.35;
}

.px-day.outside:hover {
  opacity: 0.7;
}

.px-day.today {
  border: 2px solid var(--pixel-primary);
  font-weight: 700;
}

.px-day.selected {
  background: var(--pixel-primary);
  color: var(--pixel-bg);
  border-color: var(--pixel-primary);
}

.px-day.selected:hover {
  background: var(--pixel-primary);
  color: var(--pixel-bg);
}

/* Footer */
.px-date-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 2px solid var(--pixel-border);
}

.px-footer-btn {
  background: none;
  border: 2px solid var(--pixel-border);
  color: var(--pixel-text-secondary);
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 10px;
  padding: 3px 10px;
  cursor: pointer;
  transition: border-color 0.1s, color 0.1s;
}

.px-footer-btn:hover {
  border-color: var(--pixel-primary);
  color: var(--pixel-primary);
}

.px-footer-btn.clear:hover {
  border-color: var(--pixel-accent);
  color: var(--pixel-accent);
}
</style>
