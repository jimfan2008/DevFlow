<template>
  <div class="notification-container" />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'
import { useAuthStore } from '@/stores/useAuthStore'
import { useInboxStore } from '@/stores/useInboxStore'
import { useWebSocketStore } from '@/stores/useWebSocketStore'
import type { InboxNotification } from '@/types/api'

const router = useRouter()
const authStore = useAuthStore()
const inboxStore = useInboxStore()
const wsStore = useWebSocketStore()

onMounted(() => {
  wsStore.onNotification(handleNotification)
  connectWebSocket()
})

onUnmounted(() => {
  wsStore.removeNotificationCallback()
})

function connectWebSocket() {
  if (authStore.isAuthenticated && authStore.accessToken) {
    wsStore.connect(authStore.accessToken)
  }
}

function handleNotification(notification: InboxNotification) {
  inboxStore.unreadCount++
  inboxStore.fetchNotifications()

  ElNotification({
    title: notification.title,
    message: notification.body,
    type: 'info',
    duration: 4000,
    onClick: () => {
      if (notification.task_id) {
        const boardId = notification.board_id
        if (boardId) {
          router.push({
            name: 'TaskDetail',
            params: { boardId, taskId: notification.task_id },
          })
        }
      } else {
        router.push({ name: 'Inbox' })
      }
    },
  })
}
</script>

<style lang="scss" scoped>
.notification-container {
  position: fixed;
  top: 0;
  right: 0;
  z-index: 9999;
  pointer-events: none;
}
</style>
