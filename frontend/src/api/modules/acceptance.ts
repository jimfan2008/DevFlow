import { apiClient } from '../client'
import type { ApiResponse } from '../../types/api'

export const acceptanceApi = {
  reports(params?: { project_id?: string; status?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<{ reports: Record<string, unknown>[]; total: number }>>('/acceptance', { params })
  },
  reportDetail(reportId: string) {
    return apiClient.get<ApiResponse<{ report: Record<string, unknown> }>>(`/acceptance/${reportId}`)
  },
  approve(reportId: string, data?: { comment?: string }) {
    return apiClient.post<ApiResponse<{ report: Record<string, unknown> }>>(`/acceptance/${reportId}/approve`, data)
  },
  reject(reportId: string, data: { issues: string[]; comment?: string }) {
    return apiClient.post<ApiResponse<{ report: Record<string, unknown> }>>(`/acceptance/${reportId}/reject`, data)
  },
  notifications(params?: { unread_only?: boolean; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<{ notifications: Record<string, unknown>[]; total: number; unread_count: number }>>('/acceptance/notifications', { params })
  },
  markRead(notificationId: string) {
    return apiClient.put<ApiResponse<{ id: string }>>(`/acceptance/notifications/${notificationId}/read`)
  },
  markAllRead() {
    return apiClient.put<ApiResponse<{ marked_count: number }>>('/acceptance/notifications/read-all')
  },
  deliverProject(projectId: string) {
    return apiClient.post<ApiResponse<{ delivery: Record<string, unknown> }>>(`/acceptance/projects/${projectId}/deliver`)
  },
  deliveryStatus(projectId: string) {
    return apiClient.get<ApiResponse<{ delivery: Record<string, unknown> }>>(`/acceptance/projects/${projectId}/delivery`)
  },
}
