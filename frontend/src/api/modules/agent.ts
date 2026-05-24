import { apiClient } from '../client'
import type { ApiResponse } from '../../types/api'

export const agentApi = {
  /** POST /api/agents/register - 注册 Agent */
  register(data: { name: string; agent_type: string; api_endpoint?: string; version?: string; capabilities?: Record<string, unknown>; config?: Record<string, unknown> }) {
    return apiClient.post<ApiResponse<{ agent: Record<string, unknown> }>>('/agents/register', data)
  },
  /** GET /api/agents - 获取 Agent 列表 */
  list(agentType?: string) {
    const params = agentType ? { agent_type: agentType } : undefined
    return apiClient.get<ApiResponse<{ agents: Record<string, unknown>[]; total: number }>>('/agents', { params })
  },
  /** GET /api/agents/available - 获取可用 Agent */
  available(agentType?: string) {
    const params = agentType ? { agent_type: agentType } : undefined
    return apiClient.get<ApiResponse<{ agents: Record<string, unknown>[]; total: number }>>('/agents/available', { params })
  },
  /** GET /api/agents/{agentId} - Agent 详情（含最新心跳） */
  detail(agentId: string) {
    return apiClient.get<ApiResponse<{ agent: Record<string, unknown>; latest_heartbeat: Record<string, unknown> | null }>>(`/agents/${agentId}`)
  },
  /** POST /api/agents/{agentId}/heartbeat - 心跳上报 */
  heartbeat(agentId: string, data: { load_level: number; status_detail?: Record<string, unknown> }) {
    return apiClient.post<ApiResponse<{ heartbeat: Record<string, unknown> }>>(`/agents/${agentId}/heartbeat`, data)
  },
  /** PUT /api/agents/{agentId}/status - 更新状态 */
  updateStatus(agentId: string, status: 'online' | 'offline' | 'busy') {
    return apiClient.put<ApiResponse<{ agent: Record<string, unknown> }>>(`/agents/${agentId}/status`, { status })
  },
  /** DELETE /api/agents/{agentId} - 移除 Agent */
  delete(agentId: string) {
    return apiClient.delete<ApiResponse<{ deleted: string }>>(`/agents/${agentId}`)
  },
  /** POST /api/agents/assign - 分配任务给 Agent */
  assign(taskId: string, agentId: string) {
    return apiClient.post<ApiResponse<{ execution_id: string; status: string }>>('/agents/assign', { task_id: taskId, agent_id: agentId })
  },
  /** POST /api/agents/auto-assign/{taskId} - 自动分配 */
  autoAssign(taskId: string) {
    return apiClient.post<ApiResponse<{ execution_id: string; status: string }>>(`/agents/auto-assign/${taskId}`)
  },
  /** GET /api/agents/{agentId}/load - 查询 Agent 负载 */
  load(agentId: string) {
    return apiClient.get<ApiResponse<{ load: Record<string, unknown> }>>(`/agents/${agentId}/load`)
  },
  /** POST /api/agents/{agentId}/chat - 与 Agent 直接对话 */
  chat(agentId: string, message: string) {
    return apiClient.post<ApiResponse<{ reply: string }>>(`/agents/${agentId}/chat`, { message })
  },
}

export const webhookApi = {
  /** POST /api/webhooks/hermes/status - Hermes Agent 状态变更回调 */
  hermesStatus(data: { agent_name: string; event: string; detail?: Record<string, unknown> }) {
    return apiClient.post<ApiResponse<{ agent: string; event: string }>>('/webhooks/hermes/status', data)
  },
  /** POST /api/webhooks/hermes/task-completed - Hermes Agent 任务完成通知 */
  hermesTaskCompleted(data: { agent_name: string; task_id: string; result: Record<string, unknown>; status: string }) {
    return apiClient.post<ApiResponse<{ agent_name: string; task_id: string; status: string }>>('/webhooks/hermes/task-completed', data)
  },
}
