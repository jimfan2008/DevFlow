<template>
  <div class="task-board-view">
    <div class="task-board-view__header">
      <h2 class="task-board-view__title">任务看板</h2>
      <div class="task-board-view__actions">
        <el-select v-model="selectedBoardId" placeholder="选择看板" style="width: 200px" @change="handleBoardChange">
          <el-option v-for="b in boardStore.boardList" :key="b.id" :label="b.name" :value="b.id" />
        </el-select>
        <el-button :icon="Refresh" @click="handleRefresh" :loading="taskStore.loading">刷新</el-button>
      </div>
    </div>

    <div v-if="selectedBoardId" class="task-board-view__board">
      <div v-for="status in statusColumns" :key="status.key" class="task-board-view__column">
        <div class="task-board-view__column-header">
          <span :style="{ color: status.color }">{{ status.label }}</span>
          <el-badge :value="getTasksByStatus(status.key).length" type="info" />
        </div>
        <div class="task-board-view__column-body">
          <el-card
            v-for="task in getTasksByStatus(status.key)"
            :key="task.id"
            class="task-board-view__card"
            shadow="hover"
            @click="openTaskDetail(task)"
          >
            <div class="task-board-view__card-title">{{ task.title }}</div>
            <el-progress v-if="task.progress != null" :percentage="task.progress" :stroke-width="4" style="margin-top: 8px" />
            <div v-if="task.progress_message" class="task-board-view__card-progress">{{ task.progress_message }}</div>
            <div class="task-board-view__card-meta">
              <el-tag size="small" :type="priorityType(task.priority)">{{ task.priority }}</el-tag>
              <span v-if="task.assignee" class="task-board-view__card-assignee">{{ task.assignee.display_name }}</span>
              <span v-if="task.skill_name" class="task-board-view__card-skill">Skill: {{ task.skill_name }}</span>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <div v-else class="task-board-view__empty">
      <el-empty description="请选择一个看板" />
    </div>

    <el-drawer v-model="taskDetailVisible" :title="selectedTask?.title || '任务详情'" size="480px">
      <template v-if="selectedTask">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="状态">{{ selectedTask.status }}</el-descriptions-item>
          <el-descriptions-item label="优先级">{{ selectedTask.priority }}</el-descriptions-item>
          <el-descriptions-item label="执行人">{{ selectedTask.assignee?.display_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="验收标准">{{ (selectedTask as any).acceptance_criteria || '-' }}</el-descriptions-item>
          <el-descriptions-item label="分配Skill">{{ (selectedTask as any).skill_name || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="(selectedTask as any).progress != null" style="margin-top: 16px">
          <strong>执行进度</strong>
          <el-progress :percentage="(selectedTask as any).progress" style="margin-top: 8px" />
          <p v-if="(selectedTask as any).progress_message" style="font-size: 13px; color: #909399; margin-top: 4px">{{ (selectedTask as any).progress_message }}</p>
        </div>
        <div v-if="(selectedTask as any).predecessors?.length" style="margin-top: 16px">
          <strong>前置依赖</strong>
          <div v-for="dep in (selectedTask as any).predecessors" :key="dep.id" class="task-board-view__dep-item">{{ dep.title }} ({{ dep.status }})</div>
        </div>
        <div v-if="(selectedTask as any).successors?.length" style="margin-top: 16px">
          <strong>后续任务</strong>
          <div v-for="dep in (selectedTask as any).successors" :key="dep.id" class="task-board-view__dep-item">{{ dep.title }} ({{ dep.status }})</div>
        </div>
      </template>
    </el-drawer>

    <el-dialog v-model="dagVisible" title="任务依赖关系" width="800px" top="5vh">
      <div class="task-board-view__dag" ref="dagRef">
        <el-empty v-if="taskStore.taskList.length === 0" description="暂无任务" />
        <div v-else class="task-board-view__dag-graph">
          <div v-for="task in taskStore.taskList" :key="task.id" class="task-board-view__dag-node" :style="{ borderLeftColor: getStatusColor(task.status) }">
            {{ task.title }}
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="dagVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useTaskStore } from '@/stores/useTaskStore'
import { useBoardStore } from '@/stores/useBoardStore'
import { useWebSocketStore } from '@/stores/useWebSocketStore'
import type { TaskBasic } from '@/types/api'

const taskStore = useTaskStore()
const boardStore = useBoardStore()
const wsStore = useWebSocketStore()

const selectedBoardId = ref('')
const taskDetailVisible = ref(false)
const dagVisible = ref(false)
const selectedTask = ref<TaskBasic | null>(null)
const dagRef = ref<HTMLElement | null>(null)

const statusColumns = [
  { key: 'todo', label: '待办', color: '#6b7280' },
  { key: 'in_progress', label: '进行中', color: '#3b82f6' },
  { key: 'review', label: '审核中', color: '#f59e0b' },
  { key: 'done', label: '已完成', color: '#10b981' },
]

onMounted(async () => {
  await boardStore.fetchBoardList(1, 100)
  if (boardStore.boardList.length > 0) {
    selectedBoardId.value = boardStore.boardList[0].id
    await taskStore.fetchByBoard(selectedBoardId.value)
  }
  wsStore.onNotification((notif: any) => {
    if (notif.type === 'skill_message' && selectedBoardId.value) {
      taskStore.fetchByBoard(selectedBoardId.value)
    }
  })
})

function getTasksByStatus(status: string) {
  return taskStore.taskList.filter(t => t.status === status)
}

function handleBoardChange(boardId: string) {
  taskStore.fetchByBoard(boardId)
}

function handleRefresh() {
  if (selectedBoardId.value) {
    taskStore.fetchByBoard(selectedBoardId.value)
  }
}

function openTaskDetail(task: TaskBasic) {
  selectedTask.value = task
  taskDetailVisible.value = true
  taskStore.fetchDetail(task.id)
}

function priorityType(priority: string) {
  const map: Record<string, string> = { low: 'info', medium: '', high: 'warning', urgent: 'danger' }
  return (map[priority] || 'info') as any
}

function getStatusColor(status: string) {
  const map: Record<string, string> = { todo: '#6b7280', in_progress: '#3b82f6', review: '#f59e0b', done: '#10b981' }
  return map[status] || '#6b7280'
}
</script>

<style lang="scss" scoped>
.task-board-view {
  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-6;
  }
  &__title {
    margin: 0;
    font-size: $font-size-2xl;
    font-weight: $font-weight-bold;
  }
  &__actions {
    display: flex;
    gap: $spacing-2;
  }
  &__board {
    display: flex;
    gap: $spacing-4;
    overflow-x: auto;
    min-height: 400px;
  }
  &__column {
    min-width: 260px;
    flex: 1;
    background: $bg-color-body;
    border-radius: $radius-md;
    padding: $spacing-3;
    &-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: $spacing-3;
      font-weight: $font-weight-semibold;
    }
    &-body {
      display: flex;
      flex-direction: column;
      gap: $spacing-2;
    }
  }
  &__card {
    cursor: pointer;
    &-title {
      font-weight: $font-weight-medium;
      margin-bottom: $spacing-1;
    }
    &-progress {
      font-size: $font-size-xs;
      color: $text-color-secondary;
      margin-top: 4px;
    }
    &-meta {
      display: flex;
      align-items: center;
      gap: $spacing-2;
      margin-top: $spacing-2;
      flex-wrap: wrap;
    }
    &-assignee, &-skill {
      font-size: $font-size-xs;
      color: $text-color-secondary;
    }
  }
  &__dep-item {
    font-size: $font-size-sm;
    padding: 4px 0;
    color: $text-color-secondary;
  }
  &__dag {
    min-height: 400px;
    &-graph {
      display: flex;
      flex-wrap: wrap;
      gap: $spacing-3;
    }
    &-node {
      padding: $spacing-2 $spacing-3;
      border: 1px solid $border-color-light;
      border-left-width: 4px;
      border-radius: $radius-base;
      font-size: $font-size-sm;
      background: $bg-color-card;
    }
  }
  &__empty {
    display: flex;
    justify-content: center;
    padding: 60px 0;
  }
}
</style>
