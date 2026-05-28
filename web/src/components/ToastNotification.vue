<script setup lang="ts">
import { useNotifyStore } from '../stores/notification'

const notify = useNotifyStore()

const typeConfig: Record<string, { icon: string; color: string }> = {
  success: { icon: '✓', color: 'var(--pixel-success)' },
  error: { icon: '!', color: 'var(--pixel-accent)' },
  warning: { icon: '▲', color: 'var(--pixel-warning)' },
  info: { icon: 'i', color: 'var(--pixel-info)' },
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="t in notify.toasts"
          :key="t.id"
          class="toast-item"
          :style="{ borderLeftColor: typeConfig[t.type]?.color }"
        >
          <span class="toast-icon" :style="{ color: typeConfig[t.type]?.color }">
            {{ typeConfig[t.type]?.icon }}
          </span>
          <span class="toast-msg">{{ t.message }}</span>
          <button class="toast-close" @click="notify.remove(t.id)">✕</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 60px;
  right: 16px;
  z-index: 500;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
  max-width: 340px;
}

.toast-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--pixel-card-bg);
  border: 3px solid var(--pixel-border);
  border-left: 4px solid var(--pixel-primary);
  padding: 10px 12px;
  box-shadow: 3px 3px 0 var(--pixel-shadow);
  pointer-events: auto;
  font-family: var(--font-pixel), 'Ark Pixel', monospace;
  animation: toast-in 0.2s ease-out;
}

.toast-icon {
  font-family: 'Press Start 2P', monospace;
  font-size: 10px;
  flex-shrink: 0;
  width: 16px;
  text-align: center;
}

.toast-msg {
  flex: 1;
  font-size: 12px;
  color: var(--pixel-text);
  line-height: 1.4;
}

.toast-close {
  background: none;
  border: none;
  color: var(--pixel-text-secondary);
  font-size: 12px;
  cursor: pointer;
  padding: 0 2px;
  flex-shrink: 0;
}

.toast-close:hover {
  color: var(--pixel-accent);
}

@keyframes toast-in {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

.toast-enter-active {
  animation: toast-in 0.2s ease-out;
}

.toast-leave-active {
  animation: toast-in 0.15s ease-in reverse;
}

.toast-move {
  transition: transform 0.2s ease;
}
</style>
