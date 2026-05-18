#!/bin/bash
cd /home/jim/DevFlow
exec opencode run \
  -f frontend/src/types/api.ts \
  -f frontend/src/api/index.ts \
  -f frontend/src/stores/useAuthStore.ts \
  -f frontend/src/stores/useBoardStore.ts \
  -f frontend/src/stores/useTaskStore.ts \
  -f frontend/src/stores/useInboxStore.ts \
  -f frontend/src/stores/useWebSocketStore.ts \
  -f frontend/src/router/index.js \
  -f frontend/src/App.vue \
  -f frontend/src/main.js \
  -f frontend/src/assets/styles/variables.scss \
  -f frontend_gen_prompt.md \
  '请阅读 frontend_gen_prompt.md 中的任务要求，然后生成所有缺失的前端代码文件。严格使用 @/api/index.ts 中的 API 方法，严格使用 @/types/api.ts 中的类型定义，严格对接 5 个 Pinia stores。'
