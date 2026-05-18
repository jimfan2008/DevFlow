<template>
  <div class="empty-state" :style="{ padding: `${padding}px` }">
    <el-icon :size="iconSize" :color="iconColor">
      <component :is="iconComponent" />
    </el-icon>
    <p class="empty-state__title">{{ title }}</p>
    <p v-if="description" class="empty-state__description">{{ description }}</p>
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Folder, List, Search, Edit } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  type?: 'default' | 'search' | 'inbox' | 'task'
  title?: string
  description?: string
  padding?: number
}>(), {
  type: 'default',
  title: '暂无数据',
  padding: 40,
})

const iconMap = {
  default: Folder,
  search: Search,
  inbox: List,
  task: Edit,
}

const iconComponent = computed(() => iconMap[props.type])
const iconSize = computed(() => props.type === 'default' ? 48 : 40)
const iconColor = computed(() => 'var(--el-text-color-placeholder)')
</script>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;

  &__title {
    margin-top: 16px;
    font-size: $font-size-lg;
    color: $text-color-secondary;
  }

  &__description {
    margin-top: 8px;
    font-size: $font-size-sm;
    color: $text-color-placeholder;
  }
}
</style>
