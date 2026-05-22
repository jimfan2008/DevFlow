import { apiClient } from '../client'
import type { ApiResponse } from '../../types/api'

export const repoApi = {
  list(params?: { project_id?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<{ repos: Record<string, unknown>[]; total: number }>>('/repos', { params })
  },
  detail(repoId: string) {
    return apiClient.get<ApiResponse<{ repo: Record<string, unknown> }>>(`/repos/${repoId}`)
  },
  branches(repoId: string) {
    return apiClient.get<ApiResponse<{ branches: Record<string, unknown>[] }>>(`/repos/${repoId}/branches`)
  },
  createBranch(repoId: string, data: { name: string; base: string }) {
    return apiClient.post<ApiResponse<{ branch: Record<string, unknown> }>>(`/repos/${repoId}/branches`, data)
  },
  pullRequests(repoId: string, params?: { state?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<{ pulls: Record<string, unknown>[]; total: number }>>(`/repos/${repoId}/pulls`, { params })
  },
  pullDetail(repoId: string, pullNumber: number) {
    return apiClient.get<ApiResponse<{ pull: Record<string, unknown> }>>(`/repos/${repoId}/pulls/${pullNumber}`)
  },
  commits(repoId: string, params?: { branch?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<{ commits: Record<string, unknown>[]; total: number }>>(`/repos/${repoId}/commits`, { params })
  },
  validateCommit(repoId: string, data: { message: string }) {
    return apiClient.post<ApiResponse<{ valid: boolean; errors: string[] }>>(`/repos/${repoId}/commits/validate`, data)
  },
}
