import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AcceptanceReport, AcceptanceNotification } from '@/types/api'
import { acceptanceApi } from '@/api'

export const useAcceptanceStore = defineStore('acceptance', () => {
  const reports = ref<AcceptanceReport[]>([])
  const currentReport = ref<AcceptanceReport | null>(null)
  const notifications = ref<AcceptanceNotification[]>([])
  const unreadCount = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentPage = ref(1)
  const totalItems = ref(0)

  async function fetchReports(projectId?: string, status?: string, page = 1) {
    loading.value = true
    error.value = null
    try {
      const res = await acceptanceApi.reports({ project_id: projectId, status, page, page_size: 20 }) as any
      if (res?.data?.reports) {
        reports.value = res.data.reports
        totalItems.value = res.data.total || 0
      }
    } catch (e: any) {
      error.value = e.message || '获取验收报告失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchReportDetail(reportId: string) {
    loading.value = true
    try {
      const res = await acceptanceApi.reportDetail(reportId) as any
      if (res?.data?.report) {
        currentReport.value = res.data.report
      }
    } catch (e: any) {
      error.value = e.message || '获取报告详情失败'
    } finally {
      loading.value = false
    }
  }

  async function approveReport(reportId: string, comment?: string) {
    loading.value = true
    try {
      const res = await acceptanceApi.approve(reportId, { comment }) as any
      await fetchReportDetail(reportId)
      return res?.data
    } catch (e: any) {
      error.value = e.message || '通过验收失败'
      return null
    } finally {
      loading.value = false
    }
  }

  async function rejectReport(reportId: string, issues: string[], comment?: string) {
    loading.value = true
    try {
      const res = await acceptanceApi.reject(reportId, { issues, comment }) as any
      await fetchReportDetail(reportId)
      return res?.data
    } catch (e: any) {
      error.value = e.message || '驳回验收失败'
      return null
    } finally {
      loading.value = false
    }
  }

  async function fetchNotifications(unreadOnly = false) {
    try {
      const res = await acceptanceApi.notifications({ unread_only: unreadOnly }) as any
      if (res?.data) {
        notifications.value = res.data.notifications
        unreadCount.value = res.data.unread_count || 0
      }
    } catch (e: any) {
      error.value = e.message || '获取通知失败'
    }
  }

  async function markNotificationRead(notificationId: string) {
    try {
      await acceptanceApi.markRead(notificationId)
      const n = notifications.value.find(n => n.id === notificationId)
      if (n) n.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch (e: any) {
      error.value = e.message || '标记已读失败'
    }
  }

  async function markAllNotificationsRead() {
    try {
      await acceptanceApi.markAllRead()
      notifications.value.forEach(n => { n.is_read = true })
      unreadCount.value = 0
    } catch (e: any) {
      error.value = e.message || '标记已读失败'
    }
  }

  async function deliverProject(projectId: string) {
    loading.value = true
    try {
      const res = await acceptanceApi.deliverProject(projectId) as any
      return res?.data?.delivery || null
    } catch (e: any) {
      error.value = e.message || '交付项目失败'
      return null
    } finally {
      loading.value = false
    }
  }

  return {
    reports,
    currentReport,
    notifications,
    unreadCount,
    loading,
    error,
    currentPage,
    totalItems,
    fetchReports,
    fetchReportDetail,
    approveReport,
    rejectReport,
    fetchNotifications,
    markNotificationRead,
    markAllNotificationsRead,
    deliverProject,
  }
})
