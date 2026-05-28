<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { updateProfile, uploadPortrait } from '../api/auth'
import { useAuthStore } from '../stores/auth'
import { useNotifyStore } from '../stores/notification'
import PixelDatePicker from '../components/PixelDatePicker.vue'

const router = useRouter()
const auth = useAuthStore()
const notify = useNotifyStore()

const loading = ref(false)
const error = ref('')

// Form state
const portraitFile = ref<File | null>(null)
const portraitPreview = ref('')
const characterName = ref('')
const selectedClass = ref('')
const customClass = ref('')
const isCustomClass = ref(false)
const birthday = ref('')

// Class presets
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

function selectClass(preset: typeof CLASS_PRESETS[0]) {
  selectedClass.value = `${preset.rpg}|${preset.real}`
  isCustomClass.value = false
}

function enableCustom() {
  isCustomClass.value = true
  selectedClass.value = ''
}

function onCustomInput() {
  selectedClass.value = customClass.value
}

// Zodiac
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
    if (m < z.end[0] || (m === z.end[0] && day <= z.end[1])) {
      return z
    }
  }
  return { name: '摩羯座', icon: '♑' }
})

// Portrait upload
const fileInput = ref<HTMLInputElement | null>(null)

function triggerUpload() {
  fileInput.value?.click()
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files?.length) return
  const file = target.files[0]
  if (!file.type.startsWith('image/')) return
  portraitFile.value = file
  portraitPreview.value = URL.createObjectURL(file)
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  const file = event.dataTransfer?.files[0]
  if (!file || !file.type.startsWith('image/')) return
  portraitFile.value = file
  portraitPreview.value = URL.createObjectURL(file)
}

function handleDragOver(event: DragEvent) {
  event.preventDefault()
}

// Submit
async function handleSubmit() {
  error.value = ''
  if (!characterName.value.trim()) {
    error.value = '请输入角色名称'
    return
  }
  if (!selectedClass.value) {
    error.value = '请选择一个职业'
    return
  }
  if (!birthday.value) {
    error.value = '请选择生日'
    return
  }

  loading.value = true
  try {
    if (portraitFile.value) {
      await uploadPortrait(portraitFile.value)
    }
    await updateProfile({
      character_name: characterName.value.trim(),
      character_class: selectedClass.value,
      birthday: birthday.value,
    })
    await auth.initialize()
    notify.success('角色创建成功！冒险开始！')
    router.push('/')
  } catch (e: any) {
    error.value = e?.data?.detail || '保存失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="creation-page">
    <div class="creation-card">
      <!-- Title -->
      <div class="creation-header">
        <div class="header-icon">▶</div>
        <h1 class="creation-title">角色创建</h1>
        <div class="header-sub">新建存档</div>
      </div>

      <!-- Error -->
      <div v-if="error" class="error-banner">
        <span class="error-icon">!</span>
        {{ error }}
      </div>

      <!-- Step 1: Portrait -->
      <section class="creation-section">
        <h2 class="section-title">
          <span class="step-num">01</span>
          <span class="step-label">立绘</span>
        </h2>
        <div
          class="portrait-upload"
          :class="{ 'has-image': portraitPreview }"
          @click="triggerUpload"
          @drop="handleDrop"
          @dragover="handleDragOver"
        >
          <img v-if="portraitPreview" :src="portraitPreview" alt="Portrait Preview" class="portrait-preview" />
          <div v-else class="portrait-placeholder">
            <div class="placeholder-icon">◈</div>
            <div class="placeholder-text">点击上传立绘</div>
            <div class="placeholder-sub">支持拖拽</div>
          </div>
        </div>
        <input ref="fileInput" type="file" accept="image/*" class="hidden-input" @change="handleFileSelect" />
      </section>

      <!-- Step 2: Name -->
      <section class="creation-section">
        <h2 class="section-title">
          <span class="step-num">02</span>
          <span class="step-label">角色名</span>
        </h2>
        <input
          v-model="characterName"
          type="text"
          class="pixel-input"
          placeholder="为你的角色取一个名字..."
          maxlength="50"
        />
      </section>

      <!-- Step 3: Class -->
      <section class="creation-section">
        <h2 class="section-title">
          <span class="step-num">03</span>
          <span class="step-label">职业</span>
        </h2>
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
            <span class="class-real">{{ cls.real }}</span>
          </button>
          <button class="class-card custom" :class="{ selected: isCustomClass }" @click="enableCustom">
            <span class="class-icon">✎</span>
            <span class="class-rpg">自定义</span>
            <span class="class-real">自定义职业</span>
          </button>
        </div>
        <div v-if="isCustomClass" class="custom-input-wrap">
          <input
            v-model="customClass"
            type="text"
            class="pixel-input"
            placeholder="输入自定义职业名称..."
            maxlength="100"
            @input="onCustomInput"
          />
        </div>
      </section>

      <!-- Step 4: Birthday & Zodiac -->
      <section class="creation-section">
        <h2 class="section-title">
          <span class="step-num">04</span>
          <span class="step-label">生日 / 星座</span>
        </h2>
        <div class="birthday-row">
          <PixelDatePicker v-model="birthday" placeholder="选择生日" />
          <div class="zodiac-badge" :class="{ hidden: !zodiac }">
            <span class="zodiac-icon">{{ zodiac?.icon ?? '' }}</span>
            <span class="zodiac-name">{{ zodiac?.name ?? '' }}</span>
          </div>
        </div>
      </section>

      <!-- Submit -->
      <div class="creation-actions">
        <button class="submit-btn" :disabled="loading" @click="handleSubmit">
          <span v-if="loading" class="pixel-loading inline"></span>
          <span v-else>▶ 开始冒险</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.creation-page {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  min-height: 100%;
  padding: 32px 16px;
  animation: pixel-fade-in 0.3s ease-out;
}

.creation-card {
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  box-shadow: 6px 6px 0 var(--pixel-shadow);
  padding: 32px 28px;
  max-width: 560px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Header */
.creation-header {
  text-align: center;
  padding-bottom: 16px;
  border-bottom: 3px solid var(--pixel-border);
}

.header-icon {
  font-size: 28px;
  color: var(--pixel-primary);
  margin-bottom: 8px;
  animation: pixel-blink 1.2s step-end infinite;
}

.creation-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 16px;
  color: var(--pixel-primary);
  text-shadow: 0 0 10px rgba(65, 166, 246, 0.3);
  margin: 0;
}

.header-sub {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  color: var(--pixel-text-secondary);
  letter-spacing: 2px;
  margin-top: 8px;
}

/* Error */
.error-banner {
  background: rgba(255, 107, 107, 0.1);
  border: 2px solid var(--pixel-accent);
  color: var(--pixel-accent);
  font-family: var(--font-pixel);
  font-size: 12px;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.error-icon {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--pixel-accent);
  color: var(--pixel-bg);
  flex-shrink: 0;
}

/* Sections */
.creation-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
}

.step-num {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  color: var(--pixel-primary);
  background: rgba(65, 166, 246, 0.1);
  border: 2px solid var(--pixel-primary);
  padding: 2px 8px;
}

.step-label {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  color: var(--pixel-text-secondary);
  letter-spacing: 1px;
}

/* Portrait Upload */
.portrait-upload {
  width: 160px;
  height: 208px;
  border: 3px dashed var(--pixel-border);
  background: var(--pixel-bg);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.15s ease;
  margin: 0 auto;
}

.portrait-upload:hover {
  border-color: var(--pixel-primary);
}

.portrait-upload.has-image {
  border-style: solid;
  border-color: var(--pixel-primary);
  padding: 0;
  overflow: hidden;
}

.portrait-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
  image-rendering: pixelated;
}

.portrait-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.placeholder-icon {
  font-size: 32px;
  color: var(--pixel-border);
}

.placeholder-text {
  font-family: var(--font-pixel);
  font-size: 12px;
  color: var(--pixel-text-secondary);
}

.placeholder-sub {
  font-size: 10px;
  color: var(--pixel-text-secondary);
  opacity: 0.5;
}

.hidden-input {
  display: none;
}

/* Pixel Input */
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
  box-shadow: 0 0 0 1px var(--pixel-primary);
}

.pixel-input::placeholder {
  color: var(--pixel-text-secondary);
  opacity: 0.5;
}

/* Class Grid */
.class-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.class-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 4px;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  cursor: pointer;
  transition: border-color 0.12s ease, background 0.12s ease;
  font-family: var(--font-pixel);
}

.class-card:hover {
  border-color: var(--pixel-primary);
  background: rgba(65, 166, 246, 0.05);
}

.class-card.selected {
  border-color: var(--pixel-primary);
  background: rgba(65, 166, 246, 0.12);
  box-shadow: 0 0 6px rgba(65, 166, 246, 0.15);
}

.class-icon {
  font-size: 18px;
  line-height: 1;
}

.class-rpg {
  font-size: 12px;
  font-weight: 700;
  color: var(--pixel-text);
}

.class-card.selected .class-rpg {
  color: var(--pixel-primary);
}

.class-real {
  font-size: 9px;
  color: var(--pixel-text-secondary);
  text-align: center;
  line-height: 1.2;
}

.custom-input-wrap {
  margin-top: 8px;
}

/* Birthday & Zodiac */
.birthday-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.birthday-row .pixel-input {
  flex: 1;
}

.zodiac-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  border: 2px solid var(--pixel-warning);
  background: rgba(239, 125, 87, 0.08);
  padding: 6px 12px;
  flex-shrink: 0;
  visibility: visible;
  opacity: 1;
  transition: opacity 0.15s ease, visibility 0.15s ease;
}

.zodiac-badge.hidden {
  visibility: hidden;
  opacity: 0;
}

.zodiac-icon {
  font-size: 16px;
}

.zodiac-name {
  font-family: var(--font-pixel);
  font-size: 12px;
  color: var(--pixel-warning);
  white-space: nowrap;
}

/* Submit */
.creation-actions {
  padding-top: 8px;
  border-top: 2px solid var(--pixel-border);
}

.submit-btn {
  width: 100%;
  background: var(--pixel-primary);
  border: 3px solid #2a8f87;
  color: var(--pixel-bg);
  font-family: 'Press Start 2P', monospace;
  font-size: 12px;
  padding: 14px;
  cursor: pointer;
  box-shadow: 4px 4px 0 var(--pixel-shadow);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: background 0.12s ease;
}

.submit-btn:hover {
  background: #4ecdc4;
}

.submit-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 var(--pixel-shadow);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.inline {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-width: 2px;
}

/* Responsive */
@media (max-width: 520px) {
  .creation-card {
    padding: 20px 16px;
  }

  .class-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .birthday-row {
    flex-direction: column;
    align-items: stretch;
  }

  .zodiac-badge {
    justify-content: center;
  }
}

@keyframes pixel-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pixel-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
