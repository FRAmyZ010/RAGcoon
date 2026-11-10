import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'
const usePolling = process.env.CHOKIDAR_USEPOLLING === 'true'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Listen on all interfaces so phones/PCs on the same LAN can open the app.
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    watch: {
      usePolling,
    },
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
        timeout: 1800000,
        proxyTimeout: 1800000,
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
    strictPort: true,
  },
})
