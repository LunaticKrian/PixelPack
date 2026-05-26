<script setup lang="ts">
</script>

<template>
  <div class="auth-screen">
    <div class="scanlines"></div>
    <div class="stars">
      <span v-for="i in 30" :key="i" class="star" :style="{
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 100}%`,
        animationDelay: `${Math.random() * 3}s`,
        animationDuration: `${1.5 + Math.random() * 2}s`,
      }"></span>
    </div>

    <div class="auth-container pixel-border animate-fade-in">
      <div class="auth-header">
        <div class="title-glow">
          <h1>DAILY STUFF</h1>
        </div>
        <p class="subtitle">~ 物品管理 ~</p>
      </div>

      <slot />
    </div>

    <div class="footer-text">
      <span>© 2026 DailyStuff</span>
      <span class="blink-cursor">_</span>
    </div>
  </div>
</template>

<style scoped>
.auth-screen {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--pixel-bg);
  position: relative;
  overflow: hidden;
}

.scanlines {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.08) 2px,
    rgba(0, 0, 0, 0.08) 4px
  );
  pointer-events: none;
  z-index: 10;
}

.stars {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.star {
  position: absolute;
  width: 2px;
  height: 2px;
  background: var(--pixel-text);
  animation: pixel-blink 2s step-end infinite;
  opacity: 0.4;
}

.auth-container {
  position: relative;
  z-index: 1;
  background: var(--pixel-card-bg);
  padding: 40px 48px;
  min-width: 400px;
  max-width: 480px;
  width: 90vw;
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.title-glow h1 {
  font-family: 'Press Start 2P', monospace;
  font-size: 20px;
  color: var(--pixel-primary);
  text-shadow:
    0 0 10px var(--pixel-primary),
    0 0 20px var(--pixel-primary),
    0 0 40px rgba(60, 187, 177, 0.3);
  letter-spacing: 4px;
  margin: 0;
}

.subtitle {
  font-family: var(--font-pixel);
  font-size: 14px;
  color: var(--pixel-text-secondary);
  margin-top: 12px;
  letter-spacing: 2px;
}

.footer-text {
  position: relative;
  z-index: 1;
  margin-top: 32px;
  font-family: var(--font-pixel);
  font-size: 12px;
  color: var(--pixel-text-secondary);
  opacity: 0.5;
}

.blink-cursor {
  animation: pixel-blink 0.8s step-end infinite;
}
</style>
