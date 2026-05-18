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
import type { TaskPriorityValue } from '@/types/api'

const props = withDefaults(defineProps<{
  priority: TaskPriorityValue
  size?: 'small' | 'default' | 'large'
  effect?: 'dark' | 'light' | 'plain'
}>(), {
  size: 'small',
  effect: 'light',
})

const priorityConfig: Record<TaskPriorityValue, { label: string; type: 'danger' | 'warning' | 'primary' | 'success' }> = {
  urgent: { label: '紧急', type: 'danger' },
  high: { label: '高', type: 'warning' },
  medium: { label: '中', type: 'primary' },
  low: { label: '低', type: 'success' },
}

const tagType = computed(() => priorityConfig[props.priority]?.type || 'info')
const label = computed(() => priorityConfig[props.priority]?.label || props.priority)
</script>
