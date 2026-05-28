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
        <template #title>项目管理</template>
      </el-menu-item>

      <el-menu-item index="/agents">
        <el-icon><Monitor /></el-icon>
        <template #title>Agent管理</template>
      </el-menu-item>

      <el-menu-item index="/skills">
        <el-icon><SetUp /></el-icon>
        <template #title>Skill管理</template>
      </el-menu-item>

      <el-menu-item index="/chat">
        <el-icon><ChatDotRound /></el-icon>
        <template #title>群聊会议</template>
      </el-menu-item>

      <el-menu-item index="/task-board">
        <el-icon><Grid /></el-icon>
        <template #title>任务看板</template>
      </el-menu-item>

      <el-menu-item index="/repos">
        <el-icon><Connection /></el-icon>
        <template #title>代码仓库</template>
      </el-menu-item>

      <el-sub-menu index="verify">
        <template #title>
          <el-icon><CircleCheck /></el-icon>
          <span>验收通知</span>
        </template>
        <el-menu-item index="/acceptance">验收报告</el-menu-item>
        <el-menu-item index="/notifications">
          <template #title>
            <span>通知中心</span>
            <el-badge
              v-if="unreadCount > 0"
              :value="unreadCount"
              :max="99"
              class="app-sidebar__badge"
            />
          </template>
        </el-menu-item>
        <el-menu-item index="/delivery">项目交付</el-menu-item>
      </el-sub-menu>

      <el-menu-item index="/requirements">
        <el-icon><Document /></el-icon>
        <template #title>需求管理</template>
      </el-menu-item>

      <el-menu-item index="/boards">
        <el-icon><DataBoard /></el-icon>
        <template #title>看板</template>
      </el-menu-item>

      <el-menu-item index="/inbox">
        <el-icon><Message /></el-icon>
        <template #title>收件箱</template>
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
import {
  Folder, Monitor, SetUp, ChatDotRound, Grid,
  Connection, CircleCheck, Document, DataBoard,
  Message, User
} from '@element-plus/icons-vue'
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
  overflow-y: auto;
  overflow-x: hidden;

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
