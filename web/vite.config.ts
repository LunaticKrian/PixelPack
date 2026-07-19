import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // WebRTC 信令走 WebSocket（/api/rtc/signal），必须开启 ws 代理，
        // 否则 vite dev 只转发普通 HTTP，WS 升级会卡 pending、到不了后端。
        ws: true,
      },
      '/uploads': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
