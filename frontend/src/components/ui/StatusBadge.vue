<template>
  <el-tag
    :type="tagType"
    :size="size"
    :effect="effect"
    disable-transitions
  >
    {{ label }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TaskStatusValue } from '@/types/api'

const props = withDefaults(defineProps<{
  status: TaskStatusValue
  size?: 'small' | 'default' | 'large'
  effect?: 'dark' | 'light' | 'plain'
}>(), {
  size: 'small',
  effect: 'light',
})

const statusConfig: Record<TaskStatusValue, { label: string; type: 'info' | 'primary' | 'warning' | 'success' }> = {
  todo: { label: '待办', type: 'info' },
  in_progress: { label: '进行中', type: 'primary' },
  review: { label: '审核中', type: 'warning' },
  done: { label: '已完成', type: 'success' },
}

const tagType = computed(() => statusConfig[props.status]?.type || 'info')
const label = computed(() => statusConfig[props.status]?.label || props.status)
</script>
