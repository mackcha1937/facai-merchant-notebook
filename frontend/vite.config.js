import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// 前端开发服务器配置：
// - 端口固定 5173
// - 将 /api 开头的请求代理到后端，避免跨域问题
// - 后端地址可用环境变量 VITE_BACKEND_TARGET 覆盖，默认 http://127.0.0.1:8000
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = env.VITE_BACKEND_TARGET || 'http://127.0.0.1:8000'
  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
