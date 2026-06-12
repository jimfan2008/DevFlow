<template>
  <div
    class="kanban-column"
    :class="{ 'kanban-column--drag-over': isDragOver }"
    @dragover.prevent="handleDragOver"
    @dragleave="handleDragLeave"
    @drop.prevent="handleDrop"
  >
    <div class="kanban-column__header">
      <div class="kanban-column__title">
        <span class="kanban-column__dot" :style="{ background: column.color }" />
        <span>{{ column.name }}</span>
        <el-tag size="small" type="info" effect="plain">{{ tasks.length }}</el-tag>
      </div>
      <el-dropdown trigger="click" @command="handleColumnCommand">
        <el-button :icon="MoreFilled" text size="small" />
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="edit">
              <el-icon><Edit /></el-icon>编辑
            </el-dropdown-item>
            <el-dropdown-item command="delete" divided>
              <el-icon><Delete /></el-icon>删除
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <div class="kanban-column__body" ref="bodyRef">
      <KanbanCard
        v-for="task in tasks"
        :key="task.id"
        :task="task"
        :board-id="boardId"
        @dragstart="handleCardDragStart"
        @dragend="handleCardDragEnd"
      />
    </div>

    <div class="kanban-column__footer">
      <el-button text size="small" :icon="Plus" @click="handleAddTask">
        添加任务
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { MoreFilled, Edit, Delete, Plus } from '@element-plus/icons-vue'
import KanbanCard from './KanbanCard.vue'
import type { BoardColumn, TaskBasic } from '@/types/api'

const props = defineProps<{
  column: BoardColumn
  tasks: TaskBasic[]
  boardId: string
}>()

const emit = defineEmits<{
  drop: [taskId: string, columnId: string]
  'add-task': [columnId: string]
  'edit-column': [column: BoardColumn]
  'delete-column': [columnId: string]
  'card-dragstart': [taskId: string, event: DragEvent]
  'card-dragend': []
}>()

const isDragOver = ref(false)
const bodyRef = ref<HTMLElement | null>(null)

function handleDragOver(event: DragEvent) {
  isDragOver.value = true
  event.dataTransfer!.dropEffect = 'move'
}

function handleDragLeave() {
  isDragOver.value = false
}

function handleDrop(event: DragEvent) {
  isDragOver.value = false
  const taskId = event.dataTransfer?.getData('text/plain')
  if (taskId) {
    emit('drop', taskId, props.column.id)
  }
}

function handleCardDragStart(taskId: string, event: DragEvent) {
  emit('card-dragstart', taskId, event)
}

function handleCardDragEnd() {
  emit('card-dragend')
}

function handleAddTask() {
  emit('add-task', props.column.id)
}

function handleColumnCommand(command: string) {
  if (command === 'edit') {
    emit('edit-column', props.column)
  } else if (command === 'delete') {
    emit('delete-column', props.column.id)
  }
}
</script>

<style lang="scss" scoped>
.kanban-column {
  min-width: $kanban-column-min-width;
  max-width: $kanban-column-max-width;
  width: $kanban-column-min-width;
  background: $canvas-parchment;
  border-radius: $radius-lg;
  display: flex;
  flex-direction: column;
  max-height: 100%;

  &--drag-over {
    background: rgba($primary, 0.06);
    outline: 2px dashed $primary;
  }

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: $spacing-sm $spacing-sm $spacing-xs;
    flex-shrink: 0;
  }

  &__title {
    display: flex;
    align-items: center;
    gap: $spacing-xxs;
    font-family: $font-text;
    font-size: $caption-strong-size;
    font-weight: $caption-strong-weight;
    letter-spacing: $caption-strong-tracking;
    color: $ink;
  }

  &__dot {
    width: 8px;
    height: 8px;
    border-radius: $radius-full;
    flex-shrink: 0;
  }

  &__body {
    flex: 1;
    overflow-y: auto;
    padding: 0 $spacing-xs $spacing-xs;
    min-height: 60px;
  }

  &__footer {
    padding: $spacing-xxs $spacing-sm $spacing-sm;
    flex-shrink: 0;
  }
}
</style>
