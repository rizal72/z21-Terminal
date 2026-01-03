import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Listen on all addresses (0.0.0.0)
    allowedHosts: [
      'mbp16diriccardo.tail9350d7.ts.net',
      'mbp16diriccardo',
      '.ts.net', // Allows all Tailscale domains
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      },
      '/video-feed': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
