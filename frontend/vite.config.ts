import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev server proxies /api → FastAPI on :8000 (no CORS pain in dev).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: { outDir: 'dist', sourcemap: false },
});
