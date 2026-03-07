import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/game': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/test': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
