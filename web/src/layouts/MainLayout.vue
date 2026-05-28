<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const navItems = [
  { path: '/', label: '角色信息', icon: '◈' },
]

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-shell">
    <div class="scanlines"></div>

    <!-- Top HUD Bar -->
    <header class="hud-bar">
      <div class="hud-left">
        <div class="logo">
          <span class="logo-bracket">[</span>
          <span class="logo-text">DS</span>
          <span class="logo-bracket">]</span>
        </div>
        <nav class="hud-nav">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="hud-tab"
            :class="{ active: $route.path === item.path || (item.path !== '/' && $route.path.startsWith(item.path)) }"
          >
            <span class="tab-icon">{{ item.icon }}</span>
            <span class="tab-label">{{ item.label }}</span>
          </router-link>
        </nav>
      </div>
      <div class="hud-right">
        <span class="insert-coin-mini">投币</span>
        <span class="hp-bar">
          <span class="hp-label">HP</span>
          <span class="hp-fill"></span>
        </span>
      </div>
    </header>

    <!-- Main Content -->
    <main class="content-area pixel-grid-texture">
      <slot />
    </main>

    <!-- Bottom Status Bar -->
    <footer class="hud-bottom">
      <div class="bottom-left">
        <span class="user-icon">☺</span>
        <router-link to="/settings" class="user-name">{{ auth.user?.username }}</router-link>
      </div>
      <div class="bottom-right">
        <span class="breadcrumb">
          <span class="bc-prefix">~</span>
          <span class="bc-path">/{{ $route.name }}</span>
        </span>
        <button class="logout-btn" @click="handleLogout">
          <span class="logout-icon">⏻</span>
          <span>退出</span>
        </button>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
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
  will-change: transform;
  backface-visibility: hidden;
}

/* ===== Top HUD Bar ===== */
.hud-bar {
  height: 48px;
  background: var(--pixel-bg-secondary);
  border-bottom: 3px solid var(--pixel-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
  z-index: 10;
}

.hud-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 2px;
  font-family: 'Press Start 2P', monospace;
  font-size: 14px;
}

.logo-bracket {
  color: var(--pixel-text-secondary);
}

.logo-text {
  color: var(--pixel-primary);
  text-shadow: 0 0 8px var(--pixel-primary);
  animation: pixel-text-shadow-pulse 3s ease-in-out infinite;
}

@keyframes pixel-text-shadow-pulse {
  0%, 100% {
    text-shadow: 0 0 6px var(--pixel-primary);
  }
  50% {
    text-shadow: 0 0 14px var(--pixel-primary), 0 0 28px rgba(65, 166, 246, 0.3);
  }
}

/* HUD Navigation */
.hud-nav {
  display: flex;
  align-items: center;
  gap: 4px;
}

.hud-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  color: var(--pixel-text-secondary);
  text-decoration: none;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 13px;
  border: 2px solid transparent;
  position: relative;
  transition: color 0.12s ease, border-color 0.12s ease, background 0.12s ease;
}

.hud-tab:hover {
  color: var(--pixel-text);
  background: rgba(65, 166, 246, 0.06);
  border-color: var(--pixel-border);
}

.hud-tab.active {
  color: var(--pixel-primary);
  background: rgba(65, 166, 246, 0.1);
  border-color: var(--pixel-primary);
  box-shadow: 0 2px 0 var(--pixel-primary);
}

.tab-icon {
  font-size: 14px;
  transition: transform 0.15s ease;
}

.hud-tab:hover .tab-icon {
  transform: scale(1.15);
}

.hud-tab.active .tab-icon {
  transform: scale(1.2);
}

.tab-label {
  white-space: nowrap;
}

/* HUD Right */
.hud-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.insert-coin-mini {
  font-family: 'Press Start 2P', monospace;
  font-size: 7px;
  color: var(--pixel-warning);
  animation: pixel-blink 1.5s step-end infinite;
  letter-spacing: 1px;
  opacity: 0.6;
}

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
  box-shadow: 0 0 6px rgba(56, 183, 100, 0.3);
}

/* ===== Content Area ===== */
.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

/* ===== Bottom Status Bar ===== */
.hud-bottom {
  height: 40px;
  background: var(--pixel-bg-secondary);
  border-top: 3px solid var(--pixel-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
  z-index: 10;
}

.bottom-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.user-icon {
  font-size: 16px;
}

.user-name {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  color: var(--pixel-text-secondary);
  text-decoration: none;
  transition: color 0.12s ease;
}

.user-name:hover {
  color: var(--pixel-primary);
}

.bottom-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.breadcrumb {
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 12px;
  color: var(--pixel-text-secondary);
}

.bc-prefix {
  color: var(--pixel-primary);
}

.bc-path {
  color: var(--pixel-text);
}

.logout-btn {
  background: none;
  border: 2px solid var(--pixel-accent);
  color: var(--pixel-accent);
  cursor: pointer;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  font-size: 11px;
  padding: 3px 10px;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: background 0.12s ease, color 0.12s ease;
}

.logout-btn:hover {
  background: var(--pixel-accent);
  color: var(--pixel-bg);
}

.logout-btn:active {
  transform: translate(2px, 2px);
}

/* ===== Responsive ===== */
@media (max-width: 768px) {
  .hud-bar {
    padding: 0 8px;
  }

  .tab-label {
    display: none;
  }

  .hud-tab {
    padding: 6px 10px;
  }

  .hud-left {
    gap: 8px;
  }

  .hud-nav {
    gap: 0;
  }

  .insert-coin-mini {
    display: none;
  }

  .content-area {
    padding: 16px 12px;
  }

  .hud-bottom {
    padding: 0 8px;
  }

  .breadcrumb {
    display: none;
  }
}

@keyframes pixel-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
