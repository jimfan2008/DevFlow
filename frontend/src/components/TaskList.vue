<template>
  <el-card shadow="never" class="task-list">
    <template #header>
      <div class="task-list__header">
        <span class="task-list__title">
          <el-icon style="margin-right: 4px; color: #2563eb;"><List /></el-icon>
          待办任务
          <el-tag v-if="pendingTasks.length > 0" size="small" type="primary" effect="plain" class="task-list__count">
            {{ pendingTasks.length }}
          </el-tag>
        </span>
        <el-button v-if="collapsible" text size="small" @click="expanded = !expanded">
          {{ expanded ? '收起' : '展开' }}
        </el-button>
      </div>
    </template>
    <div v-if="expanded" class="task-list__body">
      <el-empty v-if="tasks.length === 0" description="暂无待办任务" :image-size="40" />
      <div v-else class="task-list__items">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="task-list__item"
          :class="{ 'is-completed': task.status === 'completed' }"
        >
          <el-checkbox
            :model-value="task.status === 'completed'"
            @change="toggleTask(task)"
            class="task-list__checkbox"
          />
          <div class="task-list__item-body">
            <p :class="['task-list__item-desc', task.status === 'completed' ? 'is-done' : '']">
              {{ task.description }}
            </p>
            <div class="task-list__item-meta">
              <el-tag v-if="task.assignee" size="small" effect="plain" type="primary">{{ task.assignee }}</el-tag>
              <el-tag v-if="task.deadline" size="small" effect="plain" type="warning">截止: {{ task.deadline }}</el-tag>
              <el-tag
                :type="statusTagType(task.status)"
                size="small"
                effect="plain"
              >{{ statusLabel(task.status) }}</el-tag>
            </div>
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { List } from '@element-plus/icons-vue'
import type { TaskItem } from '@/types'

const props = withDefaults(defineProps<{
  tasks: TaskItem[]
  collapsible?: boolean
}>(), {
  collapsible: true,
})

const emit = defineEmits<{
  'update-status': [taskId: string, status: string]
}>()

const expanded = ref(true)

const pendingTasks = computed(() => props.tasks.filter(t => t.status !== 'completed'))

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    'pending': '待处理',
    'in_progress': '进行中',
    'completed': '已完成',
    'blocked': '阻塞',
  }
  return labels[status] || status
}

function statusTagType(status: string): 'info' | 'warning' | 'success' | 'danger' {
  const types: Record<string, 'info' | 'warning' | 'success' | 'danger'> = {
    'pending': 'info',
    'in_progress': 'warning',
    'completed': 'success',
    'blocked': 'danger',
  }
  return types[status] || 'info'
}

function toggleTask(task: TaskItem) {
  const newStatus = task.status === 'completed' ? 'pending' : 'completed'
  emit('update-status', task.id, newStatus)
}
</script>

<style lang="scss" scoped>
.task-list {
  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  &__title {
    display: flex;
    align-items: center;
    font-family: $font-text;
    font-size: $body-strong-size;
    font-weight: $body-strong-weight;
    letter-spacing: $body-strong-tracking;
    color: $ink;
  }

  &__count { margin-left: $spacing-xxs; }

  &__body { padding: 0; }

  &__items {
    border-top: 1px solid $hairline;
  }

  &__item {
    display: flex;
    align-items: flex-start;
    gap: $spacing-sm;
    padding: $spacing-sm $spacing-4;
    transition: background 0.15s;

    &:hover { background: $canvas-parchment; }

    & + & { border-top: 1px solid $hairline; }

    &.is-completed { background: mix(white, #10b981, 90%); }
  }

  &__checkbox { margin-top: 2px; }

  &__item-body {
    flex: 1;
    min-width: 0;
  }

  &__item-desc {
    margin: 0;
    font-family: $font-text;
    font-size: $body-size;
    font-weight: $body-weight;
    letter-spacing: $body-tracking;
    color: $ink;
    line-height: $body-leading;

    &.is-done {
      color: $ink-muted-48;
      text-decoration: line-through;
    }
  }

  &__item-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: $spacing-xxs;
    margin-top: $spacing-xxs;
  }
}
</style>