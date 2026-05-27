<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'

export interface PixelOption {
  value: any
  label: string
}

const props = withDefaults(defineProps<{
  modelValue: any
  options: PixelOption[]
  placeholder?: string
  width?: string
}>(), {
  placeholder: '请选择',
  width: 'auto',
})

const emit = defineEmits<{
  'update:modelValue': [value: any]
}>()

const open = ref(false)
const triggerRef = ref<HTMLElement | null>(null)
const dropdownRef = ref<HTMLElement | null>(null)

const selectedLabel = computed(() => {
  const opt = props.options.find(o => o.value === props.modelValue)
  return opt ? opt.label : props.placeholder
})

function toggle() {
  open.value = !open.value
}

function select(val: any) {
  emit('update:modelValue', val)
  open.value = false
}

function onClickOutside(e: MouseEvent) {
  if (!open.value) return
  const target = e.target as HTMLElement
  if (
    triggerRef.value?.contains(target) ||
    dropdownRef.value?.contains(target)
  ) return
  open.value = false
}

onMounted(() => {
  document.addEventListener('click', onClickOutside, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside, true)
})
</script>

<template>
  <div class="px-select" :style="{ width }">
    <div
      ref="triggerRef"
      class="px-select-trigger"
      :class="{ active: open }"
      @click="toggle"
    >
      <span class="px-select-text" :class="{ placeholder: modelValue === '' || modelValue === null || modelValue === undefined }">
        {{ selectedLabel }}
      </span>
      <span class="px-select-arrow" :class="{ open }">▼</span>
    </div>
    <div v-if="open" ref="dropdownRef" class="px-select-dropdown">
      <div
        class="px-select-option"
        :class="{ selected: modelValue === '' || modelValue === null || modelValue === undefined }"
        @click="select(options[0]?.value === undefined ? '' : null)"
      >
        {{ placeholder }}
      </div>
      <div
        v-for="opt in options"
        :key="String(opt.value)"
        class="px-select-option"
        :class="{ selected: opt.value === modelValue }"
        @click="select(opt.value)"
      >
        {{ opt.label }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.px-select {
  position: relative;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
}

.px-select-trigger {
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

.px-select-trigger:hover {
  border-color: var(--pixel-primary);
}

.px-select-trigger.active {
  border-color: var(--pixel-primary);
  box-shadow: 0 0 0 1px var(--pixel-primary);
}

.px-select-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.px-select-text.placeholder {
  color: var(--pixel-text-secondary);
  opacity: 0.5;
}

.px-select-arrow {
  font-size: 8px;
  color: var(--pixel-text-secondary);
  transition: transform 0.15s ease;
  flex-shrink: 0;
}

.px-select-arrow.open {
  transform: rotate(180deg);
}

.px-select-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 300;
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-primary);
  border-top: none;
  max-height: 220px;
  overflow-y: auto;
  animation: px-select-in 0.1s ease-out;
}

@keyframes px-select-in {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.px-select-option {
  padding: 8px 10px;
  cursor: pointer;
  color: var(--pixel-text);
  transition: background 0.08s ease, color 0.08s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  border-bottom: 1px solid var(--pixel-border);
}

.px-select-option:last-child {
  border-bottom: none;
}

.px-select-option:hover {
  background: rgba(65, 166, 246, 0.1);
  color: var(--pixel-primary);
}

.px-select-option.selected {
  background: rgba(65, 166, 246, 0.15);
  color: var(--pixel-primary);
}

.px-select-option.selected::before {
  content: '▶ ';
  font-size: 8px;
}
</style>
