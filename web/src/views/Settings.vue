<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { updateMe, changePassword } from '../api/auth'
import { useNotifyStore } from '../stores/notification'

const router = useRouter()
const auth = useAuthStore()
const notify = useNotifyStore()

// Profile form
const profileForm = reactive({
  email: auth.user?.email || '',
  avatar_url: auth.user?.avatar_url || '',
})
const profileLoading = ref(false)
const profileError = ref('')

// Password form
const pwForm = reactive({
  old_password: '',
  new_password: '',
  confirm: '',
})
const pwLoading = ref(false)
const pwError = ref('')

async function handleSaveProfile() {
  profileLoading.value = true
  profileError.value = ''
  try {
    await updateMe({
      email: profileForm.email.trim() || undefined,
      avatar_url: profileForm.avatar_url.trim() || undefined,
    })
    await auth.initialize()
    notify.success('个人信息已更新')
  } catch (e: any) {
    profileError.value = e?.data?.detail || '更新失败'
    notify.error(profileError.value)
  } finally {
    profileLoading.value = false
  }
}

async function handleChangePassword() {
  pwError.value = ''
  if (!pwForm.old_password) { pwError.value = '请输入旧密码'; return }
  if (!pwForm.new_password || pwForm.new_password.length < 6) { pwError.value = '新密码至少6位'; return }
  if (pwForm.new_password !== pwForm.confirm) { pwError.value = '两次密码不一致'; return }

  pwLoading.value = true
  try {
    await changePassword({
      old_password: pwForm.old_password,
      new_password: pwForm.new_password,
    })
    pwForm.old_password = ''
    pwForm.new_password = ''
    pwForm.confirm = ''
    notify.success('密码已修改')
  } catch (e: any) {
    pwError.value = e?.data?.detail || '修改失败'
    notify.error(pwError.value)
  } finally {
    pwLoading.value = false
  }
}
</script>

<template>
  <div class="settings-page animate-fade-in">
    <div class="settings-header">
      <button class="back-btn" @click="router.push('/')">
        <span>◀</span>
        <span>角色信息</span>
      </button>
      <h1 class="page-title">
        <span class="title-icon">◈</span>
        <span>个人设置</span>
      </h1>
    </div>

    <!-- Profile Section -->
    <div class="settings-card pixel-border">
      <div class="card-header">
        <span class="card-icon">☺</span>
        <span>基本信息</span>
      </div>
      <div class="card-body">
        <div class="field-group">
          <label class="field-label">用户名</label>
          <div class="field-readonly">{{ auth.user?.username }}</div>
        </div>
        <div class="field-group">
          <label class="field-label">邮箱</label>
          <input v-model="profileForm.email" type="email" class="pixel-input" placeholder="输入邮箱..." />
        </div>
        <div class="field-group">
          <label class="field-label">头像 URL</label>
          <input v-model="profileForm.avatar_url" type="text" class="pixel-input" placeholder="输入头像图片链接..." />
        </div>
        <div v-if="profileError" class="field-error">{{ profileError }}</div>
        <button class="pixel-btn primary" :disabled="profileLoading" @click="handleSaveProfile">
          {{ profileLoading ? '保存中...' : '✓ 保存' }}
        </button>
      </div>
    </div>

    <!-- Password Section -->
    <div class="settings-card pixel-border">
      <div class="card-header">
        <span class="card-icon">▣</span>
        <span>修改密码</span>
      </div>
      <div class="card-body">
        <div class="field-group">
          <label class="field-label">旧密码</label>
          <input v-model="pwForm.old_password" type="password" class="pixel-input" placeholder="输入旧密码" />
        </div>
        <div class="field-group">
          <label class="field-label">新密码</label>
          <input v-model="pwForm.new_password" type="password" class="pixel-input" placeholder="至少6位" />
        </div>
        <div class="field-group">
          <label class="field-label">确认密码</label>
          <input v-model="pwForm.confirm" type="password" class="pixel-input" placeholder="再次输入新密码" @keydown.enter="handleChangePassword" />
        </div>
        <div v-if="pwError" class="field-error">{{ pwError }}</div>
        <button class="pixel-btn primary" :disabled="pwLoading" @click="handleChangePassword">
          {{ pwLoading ? '修改中...' : '✓ 修改密码' }}
        </button>
      </div>
    </div>

    <!-- Account Info -->
    <div class="settings-card pixel-border">
      <div class="card-header">
        <span class="card-icon">▤</span>
        <span>账户信息</span>
      </div>
      <div class="card-body">
        <div class="field-group">
          <label class="field-label">注册时间</label>
          <div class="field-readonly">{{ auth.user?.created_at?.slice(0, 10) || '—' }}</div>
        </div>
        <div class="field-group">
          <label class="field-label">用户 ID</label>
          <div class="field-readonly">{{ auth.user?.id }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-header {
  display: flex;
  align-items: center;
  gap: 12px;
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
  white-space: nowrap;
  transition: border-color 0.12s ease, color 0.12s ease;
}

.back-btn:hover {
  border-color: var(--pixel-primary);
  color: var(--pixel-primary);
}

.back-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 var(--pixel-shadow);
}

.page-title {
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

/* Card */
.settings-card {
  background: var(--pixel-card-bg);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 2px solid var(--pixel-border);
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-text);
  user-select: none;
}

.card-icon {
  font-size: 14px;
  color: var(--pixel-primary);
  width: 18px;
  text-align: center;
}

.card-body {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Fields */
.field-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  color: var(--pixel-text-secondary);
  letter-spacing: 0.5px;
}

.field-readonly {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 13px;
  color: var(--pixel-text);
  padding: 8px 10px;
  background: var(--pixel-bg);
  border: 2px solid var(--pixel-border);
  opacity: 0.7;
}

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

.field-error {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  color: var(--pixel-accent);
  padding: 6px 8px;
  border: 2px solid var(--pixel-accent);
  background: rgba(177, 62, 83, 0.08);
}

/* Button */
.pixel-btn {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  padding: 8px 16px;
  border: 3px solid var(--pixel-border);
  background: var(--pixel-bg);
  color: var(--pixel-text);
  cursor: pointer;
  box-shadow: 3px 3px 0 var(--pixel-shadow);
  align-self: flex-start;
  transition: transform 0.08s ease, box-shadow 0.15s ease;
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
  color: var(--pixel-bg);
}

.pixel-btn.primary:hover:not(:disabled) {
  box-shadow: 3px 3px 0 var(--pixel-shadow), 0 0 6px rgba(65, 166, 246, 0.3);
}
</style>
