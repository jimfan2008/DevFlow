<template>
  <aside class="app-sidebar" :class="{ collapsed: isCollapsed }">
    <el-menu
      :default-active="activeRoute"
      :collapse="isCollapsed"
      router
      class="app-sidebar__menu"
    >
      <el-menu-item index="/projects">
        <el-icon><Folder /></el-icon>
        <template #title>项目</template>
      </el-menu-item>

      <el-menu-item index="/agents">
        <el-icon><Monitor /></el-icon>
        <template #title>Agent</template>
      </el-menu-item>

      <el-menu-item index="/skills">
        <el-icon><SetUp /></el-icon>
        <template #title>Skill</template>
      </el-menu-item>

      <el-menu-item index="/chat">
        <el-icon><ChatDotRound /></el-icon>
        <template #title>群聊</template>
      </el-menu-item>

      <el-menu-item index="/task-board">
        <el-icon><Grid /></el-icon>
        <template #title>任务</template>
      </el-menu-item>

      <el-menu-item index="/repos">
        <el-icon><Connection /></el-icon>
        <template #title>仓库</template>
      </el-menu-item>

      <el-sub-menu index="verify">
        <template #title>
          <el-icon><CircleCheck /></el-icon>
          <span>验收</span>
        </template>
        <el-menu-item index="/acceptance">验收报告</el-menu-item>
        <el-menu-item index="/notifications">
          <template #title>
            <span>通知</span>
          </template>
        </el-menu-item>
        <el-menu-item index="/delivery">交付</el-menu-item>
      </el-sub-menu>

      <el-menu-item index="/requirements">
        <el-icon><Document /></el-icon>
        <template #title>需求</template>
      </el-menu-item>

      <el-menu-item index="/boards">
        <el-icon><DataBoard /></el-icon>
        <template #title>看板</template>
      </el-menu-item>



      <el-menu-item index="/profile">
        <el-icon><User /></el-icon>
        <template #title>资料</template>
      </el-menu-item>
    </el-menu>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Folder, Monitor, SetUp, ChatDotRound, Grid,
  Connection, CircleCheck, Document, DataBoard,
  Message, User
} from '@element-plus/icons-vue'
defineProps<{
  isCollapsed?: boolean
}>()

const route = useRoute()
const activeRoute = computed(() => route.path)
</script>

<style lang="scss" scoped>
.app-sidebar {
  width: $sidebar-width;
  background: $canvas;
  border-right: 1px solid rgba(0, 0, 0, 0.06);
  transition: width 0.3s;
  overflow-y: auto;
  overflow-x: hidden;
  flex-shrink: 0;

  &.collapsed { width: $sidebar-collapsed-width; }

  &__menu {
    border-right: none;
    padding: $spacing-xs 0;

    :deep(.el-menu-item),
    :deep(.el-sub-menu__title) {
      font-family: $font-text;
      font-size: $caption-size;
      font-weight: $caption-weight;
      letter-spacing: $caption-tracking;
      color: $ink-muted-48;
      height: 40px;
      line-height: 40px;
      padding: 0 $spacing-4;
      border-radius: 0;
      margin: 1px 0;
      transition: color 0.15s, background 0.15s;

      &:hover { color: $ink; background: $canvas-parchment; }
    }

    :deep(.el-menu-item.is-active) {
      color: $primary;
      background: $canvas-parchment;
    }

    :deep(.el-sub-menu__title) {
      .el-icon { color: $ink-muted-48; }
      &:hover .el-icon { color: $ink; }
    }

    :deep(.el-menu-item .el-icon),
    :deep(.el-sub-menu__title .el-icon) {
      font-size: 16px;
      margin-right: $spacing-xs;
      width: 20px;
    }

    :deep(.el-sub-menu .el-menu) {
      background: transparent;
      .el-menu-item {
        padding-left: 52px !important;
        font-size: $fine-print-size;
      }
    }
  }

  &__badge {
    margin-left: auto;
  }
}
</style>
