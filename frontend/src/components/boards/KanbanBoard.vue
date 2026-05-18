<template>
  <div class="kanban-board">
    <div class="kanban-board__toolbar">
      <div class="kanban-board__title-section">
        <h2 class="kanban-board__title">{{ board?.name || '看板' }}</h2>
        <el-button
          v-if="board"
          size="small"
          text
          :icon="Edit"
          @click="handleEditBoard"
        >
          编辑
        </el-button>
        <el-button
          v-if="board"
          size="small"
          text
          type="danger"
          :icon="Delete"
          @click="handleDeleteBoard"
        >
          删除
        </el-button>
      </div>
      <div class="kanban-board__actions">
        <el-button size="small" :icon="Plus" @click="handleAddColumn">
          添加列
        </el-button>
      </div>
    </div>

    <div class="kanban-board__columns" v-loading="loading">
      <KanbanColumn
        v-for="column in sortedColumns"
        :key="column.id"
        :column="column"
        :tasks="getColumnTasks(column.id)"
        :board-id="boardId"
        @drop="handleDrop"
        @add-task="handleAddTask"
        @edit-column="handleEditColumn"
        @delete-column="handleDeleteColumn"
      />
    </div>

    <CreateBoardDialog
      ref="createBoardDialogRef"
      @success="handleBoardCreated"
    />

    <EditColumnDialog
      ref="editColumnDialogRef"
      :board-id="boardId"
      @success="handleColumnSaved"
    />

    <TaskForm
      ref="taskFormRef"
      :board-id="boardId"
      :initial-column-id="targetColumnId"
      @success="handleTaskCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import { useBoardStore } from '@/stores/useBoardStore'
import { useTaskStore } from '@/stores/useTaskStore'
import KanbanColumn from './KanbanColumn.vue'
import CreateBoardDialog from './CreateBoardDialog.vue'
import EditColumnDialog from './EditColumnDialog.vue'
import TaskForm from '@/components/tasks/TaskForm.vue'
import type { BoardColumn, TaskBasic } from '@/types/api'

const props = defineProps<{
  boardId: string
}>()

const router = useRouter()
const boardStore = useBoardStore()
const taskStore = useTaskStore()

const board = computed(() => boardStore.currentBoard)
const loading = computed(() => boardStore.loading || taskStore.loading)
const columns = computed(() => boardStore.columns)
const taskList = computed(() => taskStore.taskList)

const sortedColumns = computed(() =>
  [...columns.value].sort((a, b) => a.position - b.position),
)

const createBoardDialogRef = ref()
const editColumnDialogRef = ref()
const taskFormRef = ref()
const targetColumnId = ref<string | undefined>()

onMounted(async () => {
  await Promise.all([
    boardStore.fetchBoardDetail(props.boardId),
    taskStore.fetchByBoard(props.boardId),
  ])
})

function getColumnTasks(columnId: string): TaskBasic[] {
  return taskList.value.filter(t => t.column_id === columnId)
}

async function handleDrop(taskId: string, columnId: string) {
  const task = taskList.value.find(t => t.id === taskId)
  if (!task || task.column_id === columnId) return
  try {
    await taskStore.bulkMove([{ task_id: taskId, column_id: columnId }])
  } catch {
    ElMessage.error('移动任务失败')
    taskStore.fetchByBoard(props.boardId)
  }
}

function handleAddTask(columnId: string) {
  targetColumnId.value = columnId
  taskFormRef.value?.open()
}

function handleAddColumn() {
  editColumnDialogRef.value?.openForCreate()
}

function handleEditColumn(column: BoardColumn) {
  editColumnDialogRef.value?.openForEdit(column)
}

async function handleDeleteColumn(columnId: string) {
  try {
    await ElMessageBox.confirm('确定删除此列？列中的任务将不会自动删除。', '确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await boardStore.deleteColumn(props.boardId, columnId)
    ElMessage.success('列已删除')
  } catch {
    // 取消
  }
}

function handleEditBoard() {
  createBoardDialogRef.value?.openForEdit(board.value)
}

async function handleDeleteBoard() {
  try {
    await ElMessageBox.confirm(`确定删除看板"${board.value?.name}"？此操作不可撤销。`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await boardStore.deleteBoard(props.boardId)
    ElMessage.success('看板已删除')
    router.push({ name: 'BoardList' })
  } catch {
    // 取消
  }
}

function handleColumnSaved() {
  boardStore.fetchBoardDetail(props.boardId)
}

function handleTaskCreated() {
  taskStore.fetchByBoard(props.boardId)
}
</script>

<style lang="scss" scoped>
.kanban-board {
  display: flex;
  flex-direction: column;
  height: 100%;

  &__toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-4;
    flex-shrink: 0;
  }

  &__title-section {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__title {
    margin: 0;
    font-size: $font-size-2xl;
    font-weight: $font-weight-bold;
    color: $text-color-primary;
  }

  &__actions {
    display: flex;
    gap: 8px;
  }

  &__columns {
    display: flex;
    gap: $spacing-4;
    overflow-x: auto;
    flex: 1;
    padding-bottom: $spacing-4;
    align-items: flex-start;
  }
}
</style>
