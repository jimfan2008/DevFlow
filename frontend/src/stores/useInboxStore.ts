import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { InboxNotification, NotificationType } from '@/types/api'
import { acceptanceApi } from '@/api'

export const useInboxStore = defineStore('inbox', () => {
  const notifications = ref<InboxNotification[]>([])
  const unreadCount = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentPage = ref(1)
  const totalPages = ref(1)
  const totalItems = ref(0)
  const filterType = ref<NotificationType | ''>('')

  const hasData = computed(() => notifications.value.length > 0)
  const filteredNotifications = computed(() => {
    if (!filterType.value) return notifications.value
    return notifications.value.filter(n => n.type === filterType.value)
  })

  async function fetchNotifications(page = 1, pageSize = 20) {
    loading.value = true
    error.value = null
    try {
      const res: any = await acceptanceApi.notifications({ page, page_size: pageSize })
      if (res?.data) {
        notifications.value = res.data.notifications || []
        unreadCount.value = res.data.unread_count || 0
        currentPage.value = res.meta?.page || page
        totalPages.value = res.meta?.total_pages || 1
        totalItems.value = res.meta?.total || 0
      }
      return res
    } catch (e: any) {
      error.value = e.message || '获取通知失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function markRead(notificationId: string) {
    try {
      await acceptanceApi.markRead(notificationId)
      const n = notifications.value.find(n => n.id === notificationId)
      if (n) n.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch (e: any) {
      error.value = e.message || '标记已读失败'
      throw e
    }
  }

  async function markAllRead() {
    try {
      await acceptanceApi.markAllRead()
      notifications.value.forEach(n => { n.is_read = true })
      unreadCount.value = 0
    } catch (e: any) {
      error.value = e.message || '标记全部已读失败'
      throw e
    }
  }

  function setFilter(type: NotificationType | '') {
    filterType.value = type
  }

  function clearError() {
    error.value = null
  }

  return {
    notifications,
    unreadCount,
    loading,
    error,
    currentPage,
    totalPages,
    totalItems,
    filterType,
    hasData,
    filteredNotifications,
    fetchNotifications,
    markRead,
    markAllRead,
    setFilter,
    clearError,
  }
})
