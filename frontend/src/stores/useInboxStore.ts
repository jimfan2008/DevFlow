/**
 * 收件箱状态管理
 * 管理通知列表、未读数、标记已读、过滤等
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  InboxNotification,
  NotificationType,
} from '@/types/api'
import { inboxApi } from '@/api'

export const useInboxStore = defineStore('inbox', () => {
  // ==================== 状态 ====================
  const notifications = ref<InboxNotification[]>([])
  const unreadCount = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentPage = ref(1)
  const pageSize = ref(20)
  const totalItems = ref(0)
  const filterType = ref<NotificationType | 'all'>('all')
  const filterStatus = ref<'all' | 'read' | 'unread'>('all')
  const searchKeyword = ref('')

  // ==================== 计算属性 ====================
  const unreadNotifications = computed(() =>
    notifications.value.filter(n => !n.is_read),
  )

  const filteredNotifications = computed(() => {
    let result = notifications.value

    // 按类型过滤
    if (filterType.value !== 'all') {
      result = result.filter(n => n.type === filterType.value)
    }

    // 按已读/未读过滤
    if (filterStatus.value === 'read') {
      result = result.filter(n => n.is_read)
    } else if (filterStatus.value === 'unread') {
      result = result.filter(n => !n.is_read)
    }

    // 按关键词搜索
    if (searchKeyword.value) {
      const keyword = searchKeyword.value.toLowerCase()
      result = result.filter(
        n =>
          n.title.toLowerCase().includes(keyword) ||
          n.body.toLowerCase().includes(keyword),
      )
    }

    return result
  })

  const notificationTypeLabel = computed(() => ({
    assigned: '分配任务',
    comment: '新评论',
    status_change: '状态变更',
    due_reminder: '截止日期提醒',
    mention: '被提及',
  }))

  // ==================== 方法 ====================

  /**
   * 获取通知列表
   */
  async function fetchNotifications(page = 1) {
    loading.value = true
    error.value = null
    try {
      const res = await inboxApi.list({
        status: filterStatus.value,
        type: filterType.value === 'all' ? undefined : filterType.value,
        page,
        page_size: pageSize.value,
      })
      if (res.data) {
        notifications.value = res.data
        currentPage.value = res.meta?.page || 1
        totalItems.value = res.meta?.total || 0
        if ('unread_count' in res.meta) {
          unreadCount.value = (res.meta as any).unread_count
        }
      }
      return res
    } catch (e: any) {
      error.value = e.message || '获取通知失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取未读数量
   */
  async function fetchUnreadCount() {
    try {
      const res = await inboxApi.unreadCount()
      if (res.data) {
        unreadCount.value = res.data.unread_count
      }
    } catch {
      // 静默失败
    }
  }

  /**
   * 标记单条通知为已读
   */
  async function markAsRead(notificationId: string) {
    try {
      const res = await inboxApi.markAsRead(notificationId)
      if (res.data) {
        const n = notifications.value.find(n => n.id === notificationId)
        if (n) {
          n.is_read = true
        }
        unreadCount.value = Math.max(0, unreadCount.value - 1)
      }
      return res
    } catch (e: any) {
      error.value = e.message || '标记已读失败'
      throw e
    }
  }

  /**
   * 批量标记为已读
   */
  async function markAllAsRead() {
    loading.value = true
    try {
      const res = await inboxApi.markAllAsRead()
      if (res.data) {
        notifications.value.forEach(n => { n.is_read = true })
        unreadCount.value = 0
      }
      return res
    } catch (e: any) {
      error.value = e.message || '批量标记已读失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 删除通知
   */
  async function deleteNotification(notificationId: string) {
    loading.value = true
    try {
      await inboxApi.delete(notificationId)
      notifications.value = notifications.value.filter(
        n => n.id !== notificationId,
      )
      return { code: 0, message: '删除成功' }
    } catch (e: any) {
      error.value = e.message || '删除通知失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 设置过滤类型
   */
  function setFilterType(type: NotificationType | 'all') {
    filterType.value = type
    currentPage.value = 1
  }

  /**
   * 设置过滤状态
   */
  function setFilterStatus(status: 'all' | 'read' | 'unread') {
    filterStatus.value = status
    currentPage.value = 1
  }

  /**
   * 设置搜索关键词
   */
  function setSearchKeyword(keyword: string) {
    searchKeyword.value = keyword
    currentPage.value = 1
  }

  /**
   * 重置所有过滤条件
   */
  function resetFilters() {
    filterType.value = 'all'
    filterStatus.value = 'all'
    searchKeyword.value = ''
    currentPage.value = 1
  }

  // 初始化时获取未读数量（仅在已登录时）
  if (localStorage.getItem('access_token')) {
    fetchUnreadCount()
  }

  return {
    // 状态
    notifications,
    unreadCount,
    loading,
    error,
    currentPage,
    pageSize,
    totalItems,
    filterType,
    filterStatus,
    searchKeyword,
    // 计算属性
    unreadNotifications,
    filteredNotifications,
    notificationTypeLabel,
    // 方法
    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    setFilterType,
    setFilterStatus,
    setSearchKeyword,
    resetFilters,
  }
})
