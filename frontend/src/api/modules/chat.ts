import { apiClient } from '../client'
import type { ApiResponse } from '../../types/api'

export const chatApi = {
  groups(params?: { page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<{ groups: Record<string, unknown>[]; total: number }>>('/groups', { params })
  },
  createGroup(data: { name: string; members?: string[]; project_id?: string }) {
    return apiClient.post<ApiResponse<{ group: Record<string, unknown> }>>('/groups', data)
  },
  groupDetail(groupId: string) {
    return apiClient.get<ApiResponse<{ group: Record<string, unknown> }>>(`/groups/${groupId}`)
  },
  messages(groupId: string, params?: { before?: string; limit?: number }) {
    return apiClient.get<ApiResponse<{ messages: Record<string, unknown>[] }>>(`/groups/${groupId}/messages`, { params })
  },
  sendMessage(groupId: string, data: { content: string; mentions?: string[] }) {
    return apiClient.post<ApiResponse<{ message: Record<string, unknown> }>>(`/groups/${groupId}/messages`, {
      content: data.content,
      sender: 'user',
      role: 'user',
    })
  },
  startMeeting(groupId: string, data?: { agenda?: string[] }) {
    return apiClient.post<ApiResponse<{ meeting: Record<string, unknown> }>>(`/groups/${groupId}/meeting/start`, {
      topic: '技术方案评审',
      host_agent: 'default',
      meeting_type: 'tech_solution',
      pre_materials: data?.agenda,
    })
  },
  endMeeting(groupId: string) {
    return apiClient.post<ApiResponse<{ outcome: Record<string, unknown> }>>(`/groups/${groupId}/stop`, { minutes: 'Meeting completed' })
  },
}
