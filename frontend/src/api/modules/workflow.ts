import { apiClient } from '../client'
import type { ApiResponse } from '../../types/api'

export const workflowApi = {
  getStatus(projectId: string) {
    return apiClient.get<ApiResponse<Record<string, unknown>>>(`/v1/workflow/${projectId}/status`)
  },
  executeStep2(projectId: string, coreGoal: string) {
    return apiClient.post<ApiResponse<{ step: Record<string, unknown>; qa: Record<string, unknown> }>>(`/v1/workflow/${projectId}/step2`, { core_goal: coreGoal })
  },
  saveStep2Artifacts(projectId: string, data: Record<string, unknown>) {
    return apiClient.post<ApiResponse<{ message: string }>>(`/v1/workflow/${projectId}/step2/artifacts`, data)
  },
  getStep2Status(projectId: string) {
    return apiClient.get<ApiResponse<Record<string, unknown>>>(`/v1/workflow/${projectId}/step2/status`)
  },
  executeStep3(projectId: string, body?: Record<string, unknown>) {
    return apiClient.post<ApiResponse<{ step: Record<string, unknown> }>>(`/v1/workflow/${projectId}/step3`, body || {})
  },
  step3Chat(projectId: string, message: string, messages: Record<string, unknown>[]) {
    return apiClient.post<ApiResponse<{ reply: string }>>(`/v1/workflow/${projectId}/step3/chat`, { message, messages }, { timeout: 1200000 })
  },
  qaStep(projectId: string, step: number, result: 'passed' | 'failed', reason?: string, suggestions?: string[]) {
    return apiClient.post<ApiResponse<{ qa: Record<string, unknown> }>>(`/v1/workflow/${projectId}/step${step}/qa`, { result, reason, suggestions })
  },
  inspectStep3(projectId: string, content: string, focusItems?: string[]) {
    return apiClient.post<ApiResponse<{ passed: boolean; message: string; dimensions: { key: string; label: string; description: string; passed: boolean; detail: string }[] }>>(`/v1/workflow/${projectId}/step3/inspect`, { content, focus_items: focusItems }, { timeout: 120000 })
  },
  saveStep3Doc(projectId: string, content: string, filename?: string, savePath?: string) {
    return apiClient.post<ApiResponse<{ message: string; filepath: string; local_path?: string }>>(`/v1/workflow/${projectId}/step3/save-doc`, { content, filename, save_path: savePath }, { timeout: 120000 })
  },
  listStep3Docs(projectId: string, path: string) {
    return apiClient.post<ApiResponse<{ files: { name: string; path: string; content: string }[] }>>(`/v1/workflow/${projectId}/step3/list-docs`, { path })
  },
  saveStep3Artifacts(projectId: string, data: Record<string, unknown>) {
    return apiClient.post<ApiResponse<{ message: string }>>(`/v1/workflow/${projectId}/step3/artifacts`, data)
  },
  getStep3Status(projectId: string) {
    return apiClient.get<ApiResponse<Record<string, unknown>>>(`/v1/workflow/${projectId}/step3/status`)
  },
  executeStep4(projectId: string) {
    return apiClient.post<ApiResponse<{ message: string; step: Record<string, unknown> }>>(`/v1/workflow/${projectId}/step4`)
  },
  startStep4(projectId: string) {
    return apiClient.post<ApiResponse<{ message: string; status: string }>>(`/v1/workflow/${projectId}/step4/execute`)
  },
  getStep4Status(projectId: string) {
    return apiClient.get<ApiResponse<Record<string, unknown>>>(`/v1/workflow/${projectId}/step4/status`)
  },
  saveStep4Artifacts(projectId: string, data: Record<string, unknown>) {
    return apiClient.post<ApiResponse<{ message: string }>>(`/v1/workflow/${projectId}/step4/artifacts`, data)
  },
  step4Chat(projectId: string, message: string, messages: Record<string, unknown>[]) {
    return apiClient.post<ApiResponse<{ reply: string }>>(`/v1/workflow/${projectId}/step4/chat`, { message, messages }, { timeout: 1200000 })
  },
  saveStep4Doc(projectId: string, content: string, filename?: string, savePath?: string) {
    return apiClient.post<ApiResponse<{ message: string; filepath: string; local_path?: string }>>(`/v1/workflow/${projectId}/step4/save-doc`, { content, filename, save_path: savePath }, { timeout: 120000 })
  },
  listStep4Docs(projectId: string, path: string) {
    return apiClient.post<ApiResponse<{ files: { name: string; path: string; content: string }[] }>>(`/v1/workflow/${projectId}/step4/list-docs`, { path })
  },
  inspectStep4(projectId: string, content: string, focusItems?: string[]) {
    return apiClient.post<ApiResponse<{ passed: boolean; message: string; dimensions: { key: string; label: string; description: string; passed: boolean; detail: string }[] }>>(`/v1/workflow/${projectId}/step4/inspect`, { content, focus_items: focusItems }, { timeout: 120000 })
  },
}
