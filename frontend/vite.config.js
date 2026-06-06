import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // This allows Docker to expose the port
    port: 5173,
    watch: {
      usePolling: true // Ensures changes update instantly
    }
  }
})