/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    // localhost resolves to ::1 on some machines and the browser then cannot reach the server.
    host: '127.0.0.1',
    proxy: { '/api': { target: 'http://localhost:8000', ws: true } },
  },
  test: {
    environment: 'jsdom',
  },
})
