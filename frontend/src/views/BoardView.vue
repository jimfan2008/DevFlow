<template>
  <div class="board-detail-view" v-loading="pageLoading">
    <div v-if="errorMsg" class="board-detail-view__error">
      <el-result icon="error" title="加载失败" :sub-title="errorMsg">
        <template #extra>
          <el-button type="primary" @click="retry">重试</el-button>
        </template>
      </el-result>
    </div>

    <template v-else>
      <div class="board-detail-view__header">
        <div class="board-detail-view__title-row">
          <h2 class="board-detail-view__title">{{ boardName || '项目看板' }}</h2>
          <el-tag v-if="projectId" size="small" type="info">
            {{ projectId.slice(0, 8) }}...
          </el-tag>
        </div>
        <el-button size="small" text @click="refreshAll">
          <template #icon><el-icon><Refresh /></el-icon></template>
          刷新
        </el-button>
      </div>

      <HaimeiBoardPanel :board-id="boardId" />

      <el-divider>
        <el-tag size="small" effect="plain">看板列视图</el-tag>
      </el-divider>

      <KanbanBoard :board-id="boardId" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import KanbanBoard from '@/components/boards/KanbanBoard.vue'
import HaimeiBoardPanel from '@/components/boards/HaimeiBoardPanel.vue'
import { boardApi } from '@/api/modules/board'

const route = useRoute()
const boardId = computed(() => route.params.boardId as string)

const pageLoading = ref(true)
const errorMsg = ref('')
const boardName = ref('')
const projectId = ref('')

async function loadBoard() {
  pageLoading.value = true
  errorMsg.value = ''
  try {
    const res: any = await boardApi.detail(boardId.value)
    const body = res.data || res
    const boardObj = body.board || body
    boardName.value = boardObj.name || ''
    projectId.value = boardObj.project_id || ''
  } catch (e: any) {
    errorMsg.value = e?.message || '看板加载失败，请确认项目是否存在'
  } finally {
    pageLoading.value = false
  }
}

function refreshAll() {
  loadBoard()
}

function retry() {
  loadBoard()
}

onMounted(loadBoard)
</script>

<style lang="scss" scoped>
.board-detail-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow-y: auto;

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    flex-shrink: 0;
  }

  &__title-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__title {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: #1f2937;
  }

  &__error {
    display: flex;
    justify-content: center;
    align-items: center;
    flex: 1;
  }
}
</style>
