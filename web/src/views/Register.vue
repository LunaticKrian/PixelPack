<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const email = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  if (!username.value || !password.value) {
    error.value = '用户名和密码不能为空'
    return
  }
  if (password.value.length < 6) {
    error.value = '密码至少6位'
    return
  }
  if (password.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  try {
    await auth.register({
      username: username.value,
      password: password.value,
      email: email.value || undefined,
    })
    router.push('/')
  } catch (e: any) {
    error.value = e?.data?.detail || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-form">
    <div class="form-title">
      <span class="prompt">></span>
      <span>NEW GAME</span>
      <span class="blink-cursor">_</span>
    </div>

    <div class="form-fields">
      <div class="field">
        <label class="field-label">
          <span class="label-bracket">[</span>USERNAME<span class="label-bracket">]</span>
        </label>
        <input
          v-model="username"
          type="text"
          class="pixel-input"
          placeholder="起个名字..."
          autocomplete="username"
          @keyup.enter="handleRegister"
        />
      </div>

      <div class="field">
        <label class="field-label">
          <span class="label-bracket">[</span>EMAIL<span class="label-bracket">]</span>
          <span class="optional-tag">OPTIONAL</span>
        </label>
        <input
          v-model="email"
          type="email"
          class="pixel-input"
          placeholder="邮箱地址..."
          autocomplete="email"
        />
      </div>

      <div class="field">
        <label class="field-label">
          <span class="label-bracket">[</span>PASSWORD<span class="label-bracket">]</span>
        </label>
        <input
          v-model="password"
          type="password"
          class="pixel-input"
          placeholder="设置密码 (6位以上)..."
          autocomplete="new-password"
          @keyup.enter="handleRegister"
        />
      </div>

      <div class="field">
        <label class="field-label">
          <span class="label-bracket">[</span>CONFIRM<span class="label-bracket">]</span>
        </label>
        <input
          v-model="confirmPassword"
          type="password"
          class="pixel-input"
          placeholder="再次输入密码..."
          autocomplete="new-password"
          @keyup.enter="handleRegister"
        />
      </div>
    </div>

    <div v-if="error" class="error-msg">
      <span class="error-icon">!</span>
      {{ error }}
    </div>

    <button class="submit-btn" :disabled="loading" @click="handleRegister">
      <span v-if="loading" class="pixel-loading inline"></span>
      <span v-else>▶ START</span>
    </button>

    <div class="switch-link">
      <span>已有账号？</span>
      <router-link to="/login">LOGIN →</router-link>
    </div>
  </div>
</template>

<style scoped>
.register-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-title {
  font-family: 'Press Start 2P', monospace;
  font-size: 14px;
  color: var(--pixel-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.prompt {
  color: var(--pixel-accent);
}

.blink-cursor {
  animation: pixel-blink 0.8s step-end infinite;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

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
  display: flex;
  align-items: center;
  gap: 6px;
}

.label-bracket {
  color: var(--pixel-border);
}

.optional-tag {
  font-size: 7px;
  color: var(--pixel-border);
  border: 1px solid var(--pixel-border);
  padding: 1px 4px;
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
  box-shadow: 0 0 0 1px var(--pixel-primary);
}

.pixel-input::placeholder {
  color: var(--pixel-text-secondary);
  opacity: 0.5;
}

.error-msg {
  background: rgba(255, 107, 107, 0.1);
  border: 2px solid var(--pixel-accent);
  color: var(--pixel-accent);
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
}

.submit-btn {
  background: var(--pixel-primary);
  border: 3px solid #2a8f87;
  color: var(--pixel-bg);
  font-family: 'Press Start 2P', monospace;
  font-size: 12px;
  padding: 12px;
  cursor: pointer;
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.3);
  transition: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.submit-btn:hover {
  background: #4ecdc4;
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.4);
}

.submit-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 rgba(0, 0, 0, 0.3);
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

.switch-link {
  text-align: center;
  font-size: 12px;
  color: var(--pixel-text-secondary);
  display: flex;
  justify-content: center;
  gap: 8px;
}

.switch-link a {
  color: var(--pixel-primary);
  text-decoration: none;
}

.switch-link a:hover {
  text-decoration: underline;
}
</style>
