<template>
  <div
    class="kanban-card"
    :class="{ 'kanban-card--dragging': isDragging, 'kanban-card--blocked': task.blocked }"
    :draggable="true"
    @dragstart="handleDragStart"
    @dragend="handleDragEnd"
    @click="handleClick"
  >
    <div class="kanban-card__header">
      <PriorityBadge :priority="task.priority" />
      <span v-if="task.blocked" class="kanban-card__blocked">
        <el-icon><WarningFilled /></el-icon>
      </span>
    </div>

    <h4 class="kanban-card__title">{{ task.title }}</h4>

    <div class="kanban-card__tags" v-if="task.tags && task.tags.length > 0">
      <el-tag
        v-for="tag in task.tags.slice(0, 3)"
        :key="tag"
        size="small"
        type="info"
        effect="plain"
      >
        {{ tag }}
      </el-tag>
      <el-tag v-if="task.tags.length > 3" size="small" type="info">
        +{{ task.tags.length - 3 }}
      </el-tag>
    </div>

    <div class="kanban-card__footer">
      <div class="kanban-card__assignee" v-if="task.assignee">
        <el-tooltip :content="task.assignee.display_name" placement="top">
          <el-avatar :size="22">{{ task.assignee.display_name.charAt(0) }}</el-avatar>
        </el-tooltip>
      </div>
      <div class="kanban-card__meta">
        <span v-if="task.due_date" :class="{ 'is-overdue': task.due_overdue }">
          <el-icon><Calendar /></el-icon>
          {{ formatDueDate(task.due_date) }}
        </span>
        <span v-if="task.comments_count > 0">
          <el-icon><ChatDotSquare /></el-icon>
          {{ task.comments_count }}
        </span>
        <span v-if="task.attachments_count > 0">
          <el-icon><Paperclip /></el-icon>
          {{ task.attachments_count }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { WarningFilled, Calendar, ChatDotSquare, Paperclip } from '@element-plus/icons-vue'
import { format } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import PriorityBadge from '@/components/ui/PriorityBadge.vue'
import type { TaskBasic } from '@/types/api'

const props = defineProps<{
  task: TaskBasic
  boardId: string
}>()

const emit = defineEmits<{
  dragstart: [taskId: string, event: DragEvent]
  dragend: []
}>()

const router = useRouter()
const isDragging = ref(false)

function handleDragStart(event: DragEvent) {
  isDragging.value = true
  event.dataTransfer?.setData('text/plain', props.task.id)
  event.dataTransfer?.setData('column_id', props.task.column_id)
  event.dataTransfer?.effectAllowed === 'move'
  emit('dragstart', props.task.id, event)
}

function handleDragEnd() {
  isDragging.value = false
  emit('dragend')
}

function handleClick() {
  router.push({
    name: 'TaskDetail',
    params: { boardId: props.boardId, taskId: props.task.id },
  })
}

function formatDueDate(dateStr: string): string {
  try {
    return format(new Date(dateStr), 'MM/dd', { locale: zhCN })
  } catch {
    return dateStr
  }
}
</script>

<style lang="scss" scoped>
.kanban-card {
  background: $bg-color-card;
  border-radius: $radius-md;
  padding: $spacing-3;
  margin-bottom: $spacing-2;
  cursor: grab;
  box-shadow: $shadow-sm;
  border: 1px solid $border-color-light;
  transition: box-shadow 0.2s, transform 0.2s;

  &:hover {
    box-shadow: $shadow-md;
  }

  &:active {
    cursor: grabbing;
  }

  &--dragging {
    opacity: 0.5;
    transform: rotate(2deg);
  }

  &--blocked {
    border-left: 3px solid $status-blocked;
  }

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  &__blocked {
    color: $status-blocked;
  }

  &__title {
    margin: 0 0 8px;
    font-size: $font-size-base;
    font-weight: $font-weight-medium;
    color: $text-color-primary;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 8px;
  }

  &__footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  &__meta {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: $font-size-xs;
    color: $text-color-placeholder;

    .is-overdue {
      color: $status-blocked;
    }
  }

  &__assignee {
    flex-shrink: 0;
  }
}
</style>
