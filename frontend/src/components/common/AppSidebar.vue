<template>
  <aside class="app-sidebar" :class="{ collapsed: isCollapsed }">
    <el-menu
      :default-active="activeRoute"
      :collapse="isCollapsed"
      router
      class="app-sidebar__menu"
    >
      <el-menu-item index="/boards">
        <el-icon><Grid /></el-icon>
        <template #title>看板</template>
      </el-menu-item>

      <el-menu-item index="/inbox">
        <el-icon><Message /></el-icon>
        <template #title>
          <span>收件箱</span>
          <el-badge
            v-if="unreadCount > 0"
            :value="unreadCount"
            :max="99"
            class="app-sidebar__badge"
          />
        </template>
      </el-menu-item>

      <el-menu-item index="/requirements">
        <el-icon><Document /></el-icon>
        <template #title>需求管理</template>
      </el-menu-item>

      <el-menu-item index="/profile">
        <el-icon><User /></el-icon>
        <template #title>个人资料</template>
      </el-menu-item>
    </el-menu>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Grid, Message, User, Document } from '@element-plus/icons-vue'
import { useInboxStore } from '@/stores/useInboxStore'

defineProps<{
  isCollapsed?: boolean
}>()

const route = useRoute()
const inboxStore = useInboxStore()

const unreadCount = computed(() => inboxStore.unreadCount)
const activeRoute = computed(() => route.path)
</script>

<style lang="scss" scoped>
.app-sidebar {
  width: $sidebar-width;
  background: $bg-color-card;
  border-right: 1px solid $border-color-light;
  transition: width 0.3s;
  overflow: hidden;

  &.collapsed {
    width: $sidebar-collapsed-width;
  }

  &__menu {
    border-right: none;
  }

  &__badge {
    margin-left: auto;
  }
}
</style>
