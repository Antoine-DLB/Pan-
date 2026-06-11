import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, proxy API and WebSocket calls to the FastAPI backend.
const backend = process.env.VITE_BACKEND_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/health': backend,
      '/ws': {
        target: backend,
        ws: true,
      },
    },
  },
})
