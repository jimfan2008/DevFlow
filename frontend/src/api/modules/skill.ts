import { apiClient } from '../client'
import type { ApiResponse } from '../../types/api'

export const skillApi = {
  list(params?: { hermes_agent_id?: string; status?: string }) {
    return apiClient.get<ApiResponse<{ skills: Record<string, unknown>[]; total: number }>>('/skills', { params })
  },
  detail(skillId: string) {
    return apiClient.get<ApiResponse<{ skill: Record<string, unknown> }>>(`/skills/${skillId}`)
  },
  discoverAgents(skillId: string) {
    return apiClient.post<ApiResponse<{ discovered: Record<string, unknown>[] }>>(`/skills/${skillId}/discover`)
  },
  pairAgent(skillId: string, data: { agent_id: string; channel_config?: Record<string, unknown> }) {
    return apiClient.post<ApiResponse<{ pairing: Record<string, unknown> }>>(`/skills/${skillId}/pair`, data)
  },
  assignTask(skillId: string, data: { task_id: string; subtask_config?: Record<string, unknown> }) {
    return apiClient.post<ApiResponse<{ assignment: Record<string, unknown> }>>(`/skills/${skillId}/assign`, data)
  },
  history(params?: { skill_id?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<{ records: Record<string, unknown>[]; total: number }>>('/skills/history', { params })
  },
  channelStatus(skillId: string) {
    return apiClient.get<ApiResponse<{ channel: Record<string, unknown> }>>(`/skills/${skillId}/channel`)
  },
}
