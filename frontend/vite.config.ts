import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development, send API, admin and static requests to Django (same origin, so no CORS setup).
const django = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': django, '/admin': django, '/static': django },
  },
})
