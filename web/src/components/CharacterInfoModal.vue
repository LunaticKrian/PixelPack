<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { updateProfile, uploadPortrait } from '../api/auth'
import { useAuthStore } from '../stores/auth'
import { useNotifyStore } from '../stores/notification'
import PixelDatePicker from './PixelDatePicker.vue'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: [] }>()

const auth = useAuthStore()
const notify = useNotifyStore()

const loading = ref(false)
const error = ref('')

const characterName = ref('')
const selectedClass = ref('')
const customClass = ref('')
const isCustomClass = ref(false)
const birthday = ref('')
const portraitFile = ref<File | null>(null)
const portraitPreview = ref('')

const CLASS_PRESETS = [
  { rpg: '农夫', real: '程序员', icon: '♧' },
  { rpg: '魔法师', real: 'UI设计师', icon: '✦' },
  { rpg: '学者', real: '大学生', icon: '◈' },
  { rpg: '战士', real: '后端工程师', icon: '⚔' },
  { rpg: '盗贼', real: '产品经理', icon: '◎' },
  { rpg: '牧师', real: '运维工程师', icon: '✚' },
  { rpg: '猎人', real: '测试工程师', icon: '▣' },
  { rpg: '商人', real: '项目经理', icon: '◆' },
  { rpg: '吟游诗人', real: '自媒体运营', icon: '♪' },
  { rpg: '炼金术士', real: '数据分析师', icon: '⚗' },
  { rpg: '铁匠', real: '硬件工程师', icon: '⚒' },
  { rpg: '流浪者', real: '自由职业', icon: '☆' },
]

const ZODIAC_LIST = [
  { name: '摩羯座', icon: '♑', end: [1, 19] },
  { name: '水瓶座', icon: '♒', end: [2, 18] },
  { name: '双鱼座', icon: '♓', end: [3, 20] },
  { name: '白羊座', icon: '♈', end: [4, 19] },
  { name: '金牛座', icon: '♉', end: [5, 20] },
  { name: '双子座', icon: '♊', end: [6, 21] },
  { name: '巨蟹座', icon: '♋', end: [7, 22] },
  { name: '狮子座', icon: '♌', end: [8, 22] },
  { name: '处女座', icon: '♍', end: [9, 22] },
  { name: '天秤座', icon: '♎', end: [10, 23] },
  { name: '天蝎座', icon: '♏', end: [11, 22] },
  { name: '射手座', icon: '♐', end: [12, 21] },
]

const zodiac = computed(() => {
  if (!birthday.value) return null
  const d = new Date(birthday.value)
  const m = d.getMonth() + 1
  const day = d.getDate()
  for (const z of ZODIAC_LIST) {
    if (m < z.end[0] || (m === z.end[0] && day <= z.end[1])) return z
  }
  return { name: '摩羯座', icon: '♑' }
})

// Load existing data when modal opens
watch(() => props.visible, (v) => {
  if (!v) return
  error.value = ''
  portraitFile.value = null
  const u = auth.user
  characterName.value = u?.character_name || ''
  birthday.value = u?.birthday ? u.birthday.slice(0, 10) : ''
  portraitPreview.value = ''
  const cls = u?.character_class || ''
  const preset = CLASS_PRESETS.find(p => `${p.rpg}|${p.real}` === cls)
  if (preset) {
    selectedClass.value = cls
    isCustomClass.value = false
  } else if (cls) {
    selectedClass.value = cls
    customClass.value = cls
    isCustomClass.value = true
  } else {
    selectedClass.value = ''
    isCustomClass.value = false
  }
})

function selectClass(preset: typeof CLASS_PRESETS[0]) {
  selectedClass.value = `${preset.rpg}|${preset.real}`
  isCustomClass.value = false
}

function enableCustom() {
  isCustomClass.value = true
  selectedClass.value = customClass.value
}

function onCustomInput() {
  selectedClass.value = customClass.value
}

// Portrait
const fileInput = ref<HTMLInputElement | null>(null)
function triggerUpload() { fileInput.value?.click() }
function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files?.length) return
  const file = target.files[0]
  if (!file.type.startsWith('image/')) return
  portraitFile.value = file
  portraitPreview.value = URL.createObjectURL(file)
}

async function handleSave() {
  error.value = ''
  if (!characterName.value.trim()) { error.value = '请输入角色名称'; return }
  if (!selectedClass.value) { error.value = '请选择职业'; return }

  loading.value = true
  try {
    if (portraitFile.value) {
      await uploadPortrait(portraitFile.value)
    }
    await updateProfile({
      character_name: characterName.value.trim(),
      character_class: selectedClass.value,
      birthday: birthday.value || undefined,
    })
    await auth.initialize()
    notify.success('角色信息已更新')
    emit('close')
  } catch (e: any) {
    error.value = e?.data?.detail || '保存失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click.self="emit('close')">
      <div class="modal-card">
        <div class="modal-title">
          <span class="title-bracket">[</span>角色信息<span class="title-bracket">]</span>
        </div>

        <div v-if="error" class="error-banner">
          <span class="error-icon">!</span> {{ error }}
        </div>

        <!-- Portrait -->
        <div class="modal-section">
          <div class="field-label">立绘</div>
          <div class="portrait-row">
            <div class="portrait-box" @click="triggerUpload">
              <img
                v-if="portraitPreview || auth.user?.portrait_url"
                :src="portraitPreview || auth.user?.portrait_url || undefined"
                alt="Portrait"
                class="portrait-img"
              />
              <div v-else class="portrait-empty">◈</div>
            </div>
            <span class="portrait-hint">点击更换</span>
            <input ref="fileInput" type="file" accept="image/*" class="hidden-input" @change="handleFileSelect" />
          </div>
        </div>

        <!-- Name -->
        <div class="modal-section">
          <div class="field-label">角色名</div>
          <input v-model="characterName" type="text" class="pixel-input" placeholder="角色名..." maxlength="50" />
        </div>

        <!-- Class -->
        <div class="modal-section">
          <div class="field-label">职业</div>
          <div class="class-grid">
            <button
              v-for="cls in CLASS_PRESETS"
              :key="cls.rpg"
              class="class-card"
              :class="{ selected: selectedClass === `${cls.rpg}|${cls.real}` }"
              @click="selectClass(cls)"
            >
              <span class="class-icon">{{ cls.icon }}</span>
              <span class="class-rpg">{{ cls.rpg }}</span>
            </button>
            <button class="class-card custom" :class="{ selected: isCustomClass }" @click="enableCustom">
              <span class="class-icon">✎</span>
              <span class="class-rpg">自定义</span>
            </button>
          </div>
          <div v-if="isCustomClass" class="custom-wrap">
            <input v-model="customClass" type="text" class="pixel-input" placeholder="自定义职业..." @input="onCustomInput" />
          </div>
        </div>

        <!-- Birthday -->
        <div class="modal-section">
          <div class="field-label">生日 / 星座</div>
          <div class="birthday-row">
            <PixelDatePicker v-model="birthday" placeholder="选择生日" />
            <div class="zodiac-badge" :class="{ hidden: !zodiac }">
              <span class="zodiac-icon">{{ zodiac?.icon ?? '' }}</span>
              <span class="zodiac-name">{{ zodiac?.name ?? '' }}</span>
            </div>
          </div>
        </div>

        <div class="modal-actions">
          <button class="pixel-btn primary" :disabled="loading" @click="handleSave">
            <span v-if="loading" class="pixel-loading inline"></span>
            <span v-else>保存</span>
          </button>
          <button class="pixel-btn" @click="emit('close')">取消</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
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
  padding: 20px;
  min-width: 380px;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: pixel-scale-in 0.2s ease-out;
}

.modal-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 12px;
  color: var(--pixel-primary);
  letter-spacing: 1px;
}

.title-bracket { color: var(--pixel-border); }

.error-banner {
  background: rgba(255, 107, 107, 0.1);
  border: 2px solid var(--pixel-accent);
  color: var(--pixel-accent);
  font-size: 12px;
  padding: 6px 10px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.error-icon {
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  width: 14px;
  height: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--pixel-accent);
  color: var(--pixel-bg);
  flex-shrink: 0;
}

.modal-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  color: var(--pixel-text-secondary);
  letter-spacing: 1px;
}

/* Portrait */
.portrait-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.portrait-box {
  width: 64px;
  height: 84px;
  border: 2px solid var(--pixel-border);
  background: var(--pixel-bg);
  cursor: pointer;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.12s ease;
}

.portrait-box:hover { border-color: var(--pixel-primary); }

.portrait-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  image-rendering: pixelated;
}

.portrait-empty {
  font-size: 24px;
  color: var(--pixel-border);
}

.portrait-hint {
  font-size: 11px;
  color: var(--pixel-text-secondary);
}

.hidden-input { display: none; }

/* Inputs */
.pixel-input {
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  color: var(--pixel-text);
  font-family: var(--font-pixel);
  font-size: 13px;
  padding: 8px 10px;
  outline: none;
  width: 100%;
  box-sizing: border-box;
}

.pixel-input:focus {
  border-color: var(--pixel-primary);
  box-shadow: 0 0 0 1px var(--pixel-primary);
}

.pixel-input::placeholder { color: var(--pixel-text-secondary); opacity: 0.5; }

/* Class Grid */
.class-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
}

.class-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 2px;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  cursor: pointer;
  transition: border-color 0.1s ease, background 0.1s ease;
  font-family: var(--font-pixel);
}

.class-card:hover { border-color: var(--pixel-primary); }

.class-card.selected {
  border-color: var(--pixel-primary);
  background: rgba(65, 166, 246, 0.1);
}

.class-icon { font-size: 14px; }
.class-rpg { font-size: 10px; color: var(--pixel-text); }
.class-card.selected .class-rpg { color: var(--pixel-primary); }

.custom-wrap { margin-top: 6px; }

/* Birthday */
.birthday-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.birthday-row .pixel-input { flex: 1; }

.zodiac-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  border: 2px solid var(--pixel-warning);
  background: rgba(239, 125, 87, 0.08);
  padding: 4px 10px;
  flex-shrink: 0;
  visibility: visible;
  opacity: 1;
  transition: opacity 0.15s ease, visibility 0.15s ease;
}

.zodiac-badge.hidden {
  visibility: hidden;
  opacity: 0;
}

.zodiac-icon { font-size: 14px; }
.zodiac-name {
  font-family: var(--font-pixel);
  font-size: 11px;
  color: var(--pixel-warning);
  white-space: nowrap;
}

/* Buttons */
.modal-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding-top: 8px;
  border-top: 2px solid var(--pixel-border);
}

.pixel-btn {
  font-family: var(--font-pixel);
  font-size: 12px;
  padding: 8px 16px;
  border: 3px solid var(--pixel-border);
  background: var(--pixel-bg);
  color: var(--pixel-text);
  cursor: pointer;
  box-shadow: 2px 2px 0 var(--pixel-shadow);
  display: flex;
  align-items: center;
  gap: 6px;
}

.pixel-btn:hover { background: var(--pixel-card-bg); }
.pixel-btn:active { transform: translate(1px, 1px); box-shadow: 1px 1px 0 var(--pixel-shadow); }
.pixel-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.pixel-btn.primary {
  background: var(--pixel-primary);
  border-color: #2a8f87;
  color: var(--pixel-bg);
}

.pixel-btn.primary:hover { background: #4ecdc4; }

.inline {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-width: 2px;
}

@keyframes pixel-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes pixel-scale-in {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
</style>
