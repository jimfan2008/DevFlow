import { apiClient } from '../client'
import type { ApiResponse, WorkloadResponse, WorkloadMember } from '../../types/api'

export const workloadApi = {
  getBoard(boardId: string, params?: { start_date?: string; end_date?: string; include_inactive?: boolean }) {
    return apiClient.get<ApiResponse<WorkloadResponse>>(`/boards/${boardId}/workload`, { params })
  },
  getUser(userId: string, params?: { start_date?: string; end_date?: string }) {
    return apiClient.get<ApiResponse<WorkloadMember>>(`/workload/users/${userId}`, { params })
  },
  assign(taskId: string, assigneeId: string) {
    return apiClient.post<ApiResponse<{ task_id: string; old_assignee_id: string | null; new_assignee_id: string }>>(`/tasks/${taskId}/assign`, { assignee_id: assigneeId })
  },
  autoAssign(taskId: string) {
    return apiClient.post<ApiResponse<{ task: any; assigned_to: { id: string; username: string; display_name: string } }>>(`/tasks/${taskId}/assign`, { auto_assign: true })
  },
}
