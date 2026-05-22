import { apiClient } from '../client'
import type { ApiResponse, InboxListResponse, UnreadCountResponse } from '../../types/api'

export const inboxApi = {
  list(params?: { status?: 'all' | 'unread' | 'read'; type?: string; page?: number; page_size?: number }) {
    return apiClient.get<InboxListResponse>('/inbox', { params })
  },
  markAsRead(inboxId: string) {
    return apiClient.put<ApiResponse<{ id: string; is_read: boolean }>>(`/inbox/${inboxId}/read`)
  },
  markAllAsRead() {
    return apiClient.put<ApiResponse<{ marked_count: number }>>('/inbox/all/read')
  },
  delete(inboxId: string) {
    return apiClient.delete<ApiResponse<null>>(`/inbox/${inboxId}`)
  },
  unreadCount() {
    return apiClient.get<UnreadCountResponse>('/inbox/unread/count')
  },
}
