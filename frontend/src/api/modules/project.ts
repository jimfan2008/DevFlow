import { apiClient } from '../client'
import type { ApiResponse } from '../../types/api'

export const projectSrsApi = {
  /** POST /api/projects - 创建项目 */
  create(data: { name: string; description?: string; tech_stack?: Record<string, unknown> }) {
    return apiClient.post<ApiResponse<{ project: { id: string; name: string; slug: string } }>>('/projects', data)
  },
  /** GET /api/projects/{projectId}/tasks - 获取项目任务清单 */
  tasks(projectId: string) {
    return apiClient.get<ApiResponse<{ tasks: Record<string, unknown>[]; total: number; project_id: string; project_name: string }>>(`/projects/${projectId}/tasks`)
  },
  /** POST /api/projects/{projectId}/decompose - 自动拆解任务 */
  decompose(projectId: string) {
    return apiClient.post<ApiResponse<{ tasks: Record<string, unknown>[]; total: number }>>(`/projects/${projectId}/decompose`)
  },
  /** GET /api/projects/{projectId}/notifications - 获取项目通知 */
  notifications(projectId: string) {
    return apiClient.get<ApiResponse<{ notifications: Record<string, unknown>[]; total: number; unread_count: number }>>(`/projects/${projectId}/notifications`)
  },
  /** POST /api/projects/{projectId}/complete - 完成项目 */
  complete(projectId: string) {
    return apiClient.post<ApiResponse<{ project_id: string; status: string; summary: string }>>(`/projects/${projectId}/complete`)
  },
}
