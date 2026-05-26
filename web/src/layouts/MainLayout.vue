<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const sidebarOpen = ref(true)

const navItems = [
  { path: '/', label: '仪表盘', icon: '◈' },
  { path: '/items', label: '物品', icon: '◆' },
  { path: '/categories', label: '分类', icon: '▦' },
  { path: '/tags', label: '标签', icon: '◎' },
  { path: '/stats', label: '统计', icon: '▤' },
]

function handleLogout() {
  auth.logout()
  router.push('/login')
}

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}
</script>

<template>
  <div class="app-shell">
    <div class="scanlines"></div>

    <!-- Sidebar -->
    <aside class="sidebar" :class="{ collapsed: !sidebarOpen }">
      <div class="sidebar-header">
        <div class="logo" v-if="sidebarOpen">
          <span class="logo-bracket">[</span>
          <span class="logo-text">DS</span>
          <span class="logo-bracket">]</span>
        </div>
        <button class="pixel-icon-btn" @click="toggleSidebar" :title="sidebarOpen ? '收起' : '展开'">
          {{ sidebarOpen ? '◁' : '▷' }}
        </button>
      </div>

      <nav class="nav-menu">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path || (item.path !== '/' && $route.path.startsWith(item.path)) }"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label" v-if="sidebarOpen">{{ item.label }}</span>
          <span class="nav-cursor" v-if="$route.path === item.path">◄</span>
        </router-link>
      </nav>

      <div class="sidebar-footer" v-if="sidebarOpen">
        <div class="user-info">
          <span class="user-icon">☺</span>
          <span class="user-name">{{ auth.user?.username }}</span>
        </div>
        <button class="logout-btn" @click="handleLogout">
          <span class="logout-icon">⏻</span>
          <span>退出</span>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="main-area">
      <header class="top-bar">
        <div class="breadcrumb">
          <span class="bc-prefix">~</span>
          <span class="bc-path">/{{ $route.name }}</span>
        </div>
        <div class="top-bar-right">
          <span class="hp-bar">
            <span class="hp-label">HP</span>
            <span class="hp-fill" :style="{ width: '100%' }"></span>
          </span>
        </div>
      </header>

      <main class="content-area">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  position: relative;
}

.scanlines {
  position: fixed;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.06) 2px,
    rgba(0, 0, 0, 0.06) 4px
  );
  pointer-events: none;
  z-index: 100;
}

/* Sidebar */
.sidebar {
  width: 220px;
  background: var(--pixel-bg-secondary);
  border-right: 3px solid var(--pixel-border);
  display: flex;
  flex-direction: column;
  transition: width 0.15s steps(3);
  flex-shrink: 0;
}

.sidebar.collapsed {
  width: 56px;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 3px solid var(--pixel-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 2px;
  font-family: 'Press Start 2P', monospace;
  font-size: 16px;
}

.logo-bracket {
  color: var(--pixel-text-secondary);
}

.logo-text {
  color: var(--pixel-primary);
  text-shadow: 0 0 8px var(--pixel-primary);
}

.pixel-icon-btn {
  background: none;
  border: none;
  color: var(--pixel-text);
  cursor: pointer;
  font-size: 16px;
  padding: 4px;
  font-family: var(--font-pixel);
}

.pixel-icon-btn:hover {
  color: var(--pixel-primary);
}

/* Navigation */
.nav-menu {
  flex: 1;
  padding: 8px 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  color: var(--pixel-text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.1s steps(2);
  position: relative;
}

.nav-item:hover {
  color: var(--pixel-text);
  background: rgba(60, 187, 177, 0.08);
}

.nav-item.active {
  color: var(--pixel-primary);
  background: rgba(60, 187, 177, 0.12);
}

.nav-icon {
  font-size: 16px;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.nav-label {
  flex: 1;
}

.nav-cursor {
  font-size: 10px;
  animation: pixel-blink 0.8s step-end infinite;
}

/* Sidebar Footer */
.sidebar-footer {
  padding: 12px 16px;
  border-top: 3px solid var(--pixel-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.user-icon {
  font-size: 18px;
}

.logout-btn {
  background: none;
  border: 2px solid var(--pixel-accent);
  color: var(--pixel-accent);
  cursor: pointer;
  font-family: var(--font-pixel);
  font-size: 11px;
  padding: 4px 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.logout-btn:hover {
  background: var(--pixel-accent);
  color: var(--pixel-bg);
}

.logout-btn:active {
  transform: translate(2px, 2px);
}

/* Main Area */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.top-bar {
  height: 44px;
  background: var(--pixel-bg-secondary);
  border-bottom: 3px solid var(--pixel-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
}

.breadcrumb {
  font-family: var(--font-pixel);
  font-size: 13px;
  color: var(--pixel-text-secondary);
}

.bc-prefix {
  color: var(--pixel-primary);
}

.bc-path {
  color: var(--pixel-text);
}

/* HP bar - decorative RPG element */
.hp-bar {
  display: flex;
  align-items: center;
  gap: 6px;
}

.hp-label {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  color: var(--pixel-success);
}

.hp-fill {
  width: 60px;
  height: 8px;
  background: var(--pixel-success);
  box-shadow: 0 0 6px rgba(107, 203, 119, 0.4);
  transition: width 0.3s steps(4);
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
</style>
