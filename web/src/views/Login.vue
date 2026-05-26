<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  if (!username.value || !password.value) {
    error.value = '请填写所有字段'
    return
  }
  loading.value = true
  try {
    await auth.login({ username: username.value, password: password.value })
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (e: any) {
    error.value = e?.data?.detail || '登录失败，请检查用户名和密码'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-form">
    <div class="form-title">
      <span class="prompt">></span>
      <span>LOGIN</span>
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
          placeholder="输入用户名..."
          autocomplete="username"
          @keyup.enter="handleLogin"
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
          placeholder="输入密码..."
          autocomplete="current-password"
          @keyup.enter="handleLogin"
        />
      </div>
    </div>

    <div v-if="error" class="error-msg">
      <span class="error-icon">!</span>
      {{ error }}
    </div>

    <button class="submit-btn" :disabled="loading" @click="handleLogin">
      <span v-if="loading" class="pixel-loading inline"></span>
      <span v-else>▶ LOGIN</span>
    </button>

    <div class="switch-link">
      <span>还没有账号？</span>
      <router-link to="/register">REGISTER →</router-link>
    </div>
  </div>
</template>

<style scoped>
.login-form {
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
  gap: 16px;
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
}

.label-bracket {
  color: var(--pixel-border);
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
