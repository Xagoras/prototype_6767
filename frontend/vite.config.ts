import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// 开发环境将 /api 代理到 FastAPI 后端（localhost:8000）
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
