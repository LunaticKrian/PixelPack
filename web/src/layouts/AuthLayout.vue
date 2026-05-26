<script setup lang="ts">
</script>

<template>
  <div class="auth-screen pixel-vignette">
    <!-- Stronger CRT scanlines -->
    <div class="scanlines-crt"></div>

    <!-- Animated scanline sweep -->
    <div class="scanline-sweep"></div>

    <!-- Floating stars -->
    <div class="stars">
      <span
        v-for="i in 40"
        :key="i"
        class="star"
        :style="{
          left: `${Math.random() * 100}%`,
          top: `${Math.random() * 100}%`,
          animationDelay: `${Math.random() * 3}s`,
          animationDuration: `${1.5 + Math.random() * 2}s`,
        }"
      ></span>
    </div>

    <!-- Pixel grid overlay -->
    <div class="pixel-grid-overlay"></div>

    <!-- Auth container -->
    <div class="auth-container pixel-border animate-scale-in">
      <div class="auth-header">
        <div class="title-glow">
          <h1>DAILY STUFF</h1>
        </div>
        <p class="subtitle">~ 物品管理 ~</p>
        <div class="insert-coin-text">INSERT COIN TO START</div>
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

/* Stronger CRT scanlines for auth pages */
.scanlines-crt {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 1px,
    rgba(0, 0, 0, 0.12) 1px,
    rgba(0, 0, 0, 0.12) 3px
  );
  pointer-events: none;
  z-index: 10;
}

/* Moving scanline bar */
.scanline-sweep {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 11;
}

.scanline-sweep::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  height: 60px;
  background: linear-gradient(
    transparent,
    rgba(65, 166, 246, 0.04),
    rgba(65, 166, 246, 0.06),
    rgba(65, 166, 246, 0.04),
    transparent
  );
  animation: scanline-move 6s linear infinite;
}

@keyframes scanline-move {
  0% { top: -60px; }
  100% { top: 100%; }
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

/* Subtle pixel grid overlay */
.pixel-grid-overlay {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.015) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.015) 1px, transparent 1px);
  background-size: 8px 8px;
  pointer-events: none;
  z-index: 1;
}

.auth-container {
  position: relative;
  z-index: 2;
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
    0 0 40px rgba(65, 166, 246, 0.25);
  letter-spacing: 4px;
  margin: 0;
  animation: pixel-text-shadow-pulse 3s ease-in-out infinite;
}

@keyframes pixel-text-shadow-pulse {
  0%, 100% {
    text-shadow:
      0 0 10px var(--pixel-primary),
      0 0 20px var(--pixel-primary),
      0 0 40px rgba(65, 166, 246, 0.25);
  }
  50% {
    text-shadow:
      0 0 14px var(--pixel-primary),
      0 0 28px var(--pixel-primary),
      0 0 56px rgba(65, 166, 246, 0.35);
  }
}

.subtitle {
  font-family: var(--font-pixel);
  font-size: 14px;
  color: var(--pixel-text-secondary);
  margin-top: 12px;
  letter-spacing: 2px;
}

.insert-coin-text {
  font-family: 'Press Start 2P', monospace;
  font-size: 8px;
  color: var(--pixel-warning);
  margin-top: 16px;
  letter-spacing: 2px;
  animation: pixel-blink 1.2s step-end infinite;
  opacity: 0.7;
}

.footer-text {
  position: relative;
  z-index: 2;
  margin-top: 32px;
  font-family: var(--font-pixel);
  font-size: 12px;
  color: var(--pixel-text-secondary);
  opacity: 0.5;
}

.blink-cursor {
  animation: pixel-blink 0.8s step-end infinite;
}

@keyframes pixel-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
