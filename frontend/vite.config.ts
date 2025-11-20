import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: process.env.PORT ? parseInt(process.env.PORT) : 5173,
    strictPort: false,
    allowedHosts: [
      'color-stealer-frontend.onrender.com',
      '.onrender.com', // Allow all Render subdomains
      'localhost'
    ],
    proxy: {
        '/api': {
            target: process.env.VITE_API_URL || 'http://backend:8000',
            changeOrigin: true,
        }
    }
  }
})
