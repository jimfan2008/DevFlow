import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import fs from 'fs'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// 从 .env 读取后端端口，不写死任何默认值
const envPath = path.resolve(__dirname, '..', '.env')
let backendPort = ''
try {
  const envContent = fs.readFileSync(envPath, 'utf-8')
  const match = envContent.match(/^BACKEND_PORT=(\S+)/m)
  if (match) backendPort = match[1]
} catch {}

if (!backendPort) {
  throw new Error(`BACKEND_PORT 未在 ${envPath} 中配置。请在 .env 中设置 BACKEND_PORT=端口号`)
}

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      imports: ['vue', 'vue-router', 'pinia'],
      resolvers: [ElementPlusResolver()],
      dts: 'src/auto-imports.d.ts'
    }),
    Components({
      resolvers: [ElementPlusResolver()]
    })
  ],
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/assets/styles/variables" as *;`,
        api: 'modern'
      }
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    exclude: ['tests/e2e/**', 'node_modules/**'],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      }
    },
    server: {
      deps: {
        inline: ['element-plus'],
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
        ws: true
      },
      '/ws': {
        target: `ws://localhost:${backendPort}`,
        ws: true,
        changeOrigin: true
      },
      '/auth': {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true
      },
      '/step4': {
        target: `http://localhost:${backendPort}`,
        ws: true,
        changeOrigin: true
      },
      '/step5': {
        target: `http://localhost:${backendPort}`,
        ws: true,
        changeOrigin: true
      },
      '/step6': {
        target: `http://localhost:${backendPort}`,
        ws: true,
        changeOrigin: true
      },
      '/step7': {
        target: `http://localhost:${backendPort}`,
        ws: true,
        changeOrigin: true
      },
      '/step8': {
        target: `http://localhost:${backendPort}`,
        ws: true,
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1000
  }
})
