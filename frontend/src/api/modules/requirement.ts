import { apiClient } from '../client'
import type { ApiResponse } from '../../types/api'

export const requirementApi = {
  /** PUT /api/projects/{projectId}/requirements - 提交需求 */
  submit(projectId: string, data: { content: string; project_name?: string; tech_stack?: Record<string, unknown> }) {
    return apiClient.put<ApiResponse<{ requirement: Record<string, unknown> }>>(`/projects/${projectId}/requirements`, data)
  },
  /** GET /api/projects/{projectId}/requirements - 获取需求 */
  get(projectId: string) {
    return apiClient.get<ApiResponse<{ requirement: Record<string, unknown> }>>(`/projects/${projectId}/requirements`)
  },
  /** POST /api/projects/{projectId}/requirements/clarify - Hermes Agent 需求澄清 */
  clarify(projectId: string, data: { project_name: string; features: string[]; tech_stack?: Record<string, unknown> }) {
    return apiClient.post<ApiResponse<{ document: Record<string, unknown> }>>(`/projects/${projectId}/requirements/clarify`, data)
  },
  /** POST /api/projects/{projectId}/requirements/confirm - 确认需求 */
  confirm(projectId: string) {
    return apiClient.post<ApiResponse<Record<string, unknown>>>(`/projects/${projectId}/requirements/confirm`, { confirmed: true })
  },
}
