import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  server: { port: 5173, strictPort: true },
  plugins: [react(), tailwindcss()],
})
