import { apiClient } from '../client'
import type { ApiResponse } from '../../types/api'

export const executionApi = {
  /** POST /api/tasks/{taskId}/deliver - 交付任务成果 */
  deliver(taskId: string, result: Record<string, unknown>) {
    return apiClient.post<ApiResponse<{ execution_id: string; status: string }>>(`/tasks/${taskId}/deliver`, { result })
  },
  /** POST /api/tasks/{taskId}/accept - 验收任务成果 */
  accept(taskId: string) {
    return apiClient.post<ApiResponse<{ acceptance_id: string; result: string; checks: Record<string, unknown>; suggestions: string[] }>>(`/tasks/${taskId}/accept`)
  },
  /** GET /api/tasks/{taskId}/executions - 获取任务执行记录 */
  executions(taskId: string) {
    return apiClient.get<ApiResponse<{ executions: Record<string, unknown>[]; total: number }>>(`/tasks/${taskId}/executions`)
  },
}
