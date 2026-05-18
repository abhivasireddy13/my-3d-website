import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/my-3d-website/',
  cacheDir: './node_modules/.vite2',
  resolve: {
    dedupe: ['react', 'react-dom'],
  },
})
