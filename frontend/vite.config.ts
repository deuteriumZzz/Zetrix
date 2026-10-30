import { resolve } from 'node:path'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

// / stays the public landing. /app/* always loads the separate cabinet entry.
function cabinetRoutes(): Plugin {
  const install = (server: { middlewares: { use: Function } }) => {
    server.middlewares.use((request: { url?: string }, _response: unknown, next: () => void) => {
      const [path, query] = (request.url ?? '').split('?')
      if ((path === '/app' || path.startsWith('/app/')) && !path.split('/').pop()?.includes('.')) {
        request.url = `/app/index.html${query ? `?${query}` : ''}`
      }
      next()
    })
  }
  return { name: 'zetrix-cabinet-routes', configureServer: install, configurePreviewServer: install }
}

export default defineConfig({
  plugins: [react(), cabinetRoutes()],
  build: { rollupOptions: { input: {
    landing: resolve(__dirname, 'index.html'),
    cabinet: resolve(__dirname, 'app/index.html'),
  } } },
  server: {
    port: 5173,
    proxy: {
      // Preserve the browser's Host so Django's same-origin CSRF check stays valid.
      '/api': { target: process.env.ZETRIX_API_TARGET || 'http://127.0.0.1:8000', changeOrigin: false },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
})
