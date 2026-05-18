<template>
  <el-tooltip :content="tooltip" placement="top" :disabled="!showTooltip">
    <div class="workload-badge" :class="levelClass">
      <el-icon v-if="level === 'overload'" :size="14"><WarningFilled /></el-icon>
      <el-icon v-else-if="level === 'underload'" :size="14"><InfoFilled /></el-icon>
      <el-icon v-else :size="14"><CircleCheck /></el-icon>
      <span class="workload-badge__text">{{ label }}</span>
    </div>
  </el-tooltip>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { WarningFilled, InfoFilled, CircleCheck } from '@element-plus/icons-vue'

const props = defineProps<{
  overload?: boolean
  underload?: boolean
  completionRatio?: number
  showTooltip?: boolean
}>()

const level = computed(() => {
  if (props.overload) return 'overload'
  if (props.underload) return 'underload'
  return 'normal'
})

const levelClass = computed(() => `workload-badge--${level.value}`)

const label = computed(() => {
  if (props.overload) return '过载'
  if (props.underload) return '空闲'
  return '正常'
})

const tooltip = computed(() => {
  const ratio = props.completionRatio !== undefined ? Math.round(props.completionRatio * 100) : '--'
  return `完成率: ${ratio}%`
})
</script>

<style lang="scss" scoped>
.workload-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: $radius-full;
  font-size: $font-size-xs;
  font-weight: $font-weight-medium;

  &--overload {
    background: rgba($workload-busy, 0.1);
    color: $workload-busy;
  }

  &--underload {
    background: rgba($workload-idle, 0.1);
    color: $workload-idle;
  }

  &--normal {
    background: rgba($workload-normal, 0.1);
    color: $workload-normal;
  }
}
</style>
