import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Çıktı, Python sunucusunun servis ettiği ../web klasörüne derlenir.
// base './' => hem 127.0.0.1 hem LAN üzerinden göreli yollarla çalışır.
export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  build: {
    outDir: '../web',
    emptyOutDir: true,
    assetsDir: 'panel',
  },
  server: {
    proxy: {
      '/data': 'http://127.0.0.1:1100',
      '/info': 'http://127.0.0.1:1100',
      '/quit': 'http://127.0.0.1:1100',
      '/lang': 'http://127.0.0.1:1100',
    },
  },
})
