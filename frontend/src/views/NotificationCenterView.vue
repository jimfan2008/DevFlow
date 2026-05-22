<template>
  <div class="notification-center-view">
    <div class="notification-center-view__header">
      <h2 class="notification-center-view__title">通知中心</h2>
      <div class="notification-center-view__actions">
        <el-badge :value="store.unreadCount" :hidden="store.unreadCount === 0" :max="99">
          <el-button size="small">未读</el-button>
        </el-badge>
        <el-button size="small" :disabled="store.unreadCount === 0" @click="handleMarkAllRead">全部已读</el-button>
        <el-button size="small" @click="handleRefresh">刷新</el-button>
      </div>
    </div>

    <el-table :data="store.notifications" stripe v-loading="store.loading">
      <el-table-column label="" width="40">
        <template #default="{ row }">
          <span v-if="!row.is_read" class="notification-center-view__unread-dot" />
        </template>
      </el-table-column>
      <el-table-column prop="type" label="类型" width="120" />
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="body" label="内容" show-overflow-tooltip />
      <el-table-column prop="created_at" label="时间" width="180">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button v-if="!row.is_read" size="small" text type="primary" @click="handleMarkRead(row.id)">标为已读</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!store.loading && store.notifications.length === 0" description="暂无通知" />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAcceptanceStore } from '@/stores/useAcceptanceStore'

const store = useAcceptanceStore()

onMounted(() => {
  store.fetchNotifications()
})

async function handleMarkRead(notificationId: string) {
  await store.markNotificationRead(notificationId)
  ElMessage.success('已标记为已读')
}

async function handleMarkAllRead() {
  await store.markAllNotificationsRead()
  ElMessage.success('已全部标记为已读')
}

function handleRefresh() {
  store.fetchNotifications()
}

function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN')
}
</script>

<style lang="scss" scoped>
.notification-center-view {
  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-6;
  }
  &__title {
    margin: 0;
    font-size: $font-size-2xl;
    font-weight: $font-weight-bold;
  }
  &__actions {
    display: flex;
    align-items: center;
    gap: $spacing-2;
  }
  &__unread-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: $primary-color;
  }
}
</style>
