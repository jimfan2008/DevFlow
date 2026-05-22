import { apiClient } from '../client'
import type { ApiResponse, PaginatedResponse, TaskFull, TaskBasic, TaskCreateRequest, TaskUpdateRequest, TaskBulkMoveRequest, TaskBulkMoveResponse, TaskSearchRequest, TaskSearchResponse, CommentCreateRequest, CommentItem, DependencyCreateRequest, TaskBrief, AttachmentCreateResponse } from '../../types/api'

export const taskApi = {
  create(data: TaskCreateRequest) {
    return apiClient.post<ApiResponse<TaskFull>>('/tasks', data)
  },
  list(params?: { board_id?: string; column_id?: string; status?: string; assignee_id?: string; priority?: string; tags?: string; search?: string; created_after?: string; due_before?: string; page?: number; page_size?: number }) {
    return apiClient.get<PaginatedResponse<TaskBasic>>('/tasks', { params })
  },
  byBoard(boardId: string, params?: { page_size?: number }) {
    return apiClient.get<ApiResponse<TaskBasic[]>>('/tasks', { params: { board_id: boardId, ...(params || {}), page_size: params?.page_size || 200 } })
  },
  detail(taskId: string) {
    return apiClient.get<ApiResponse<TaskFull>>(`/tasks/${taskId}`)
  },
  update(taskId: string, data: TaskUpdateRequest) {
    return apiClient.patch<ApiResponse<TaskFull>>(`/tasks/${taskId}`, data)
  },
  delete(taskId: string) {
    return apiClient.delete<ApiResponse<null>>(`/tasks/${taskId}`)
  },
  bulkMove(data: TaskBulkMoveRequest) {
    return apiClient.post<ApiResponse<TaskBulkMoveResponse>>('/tasks/bulk-move', data)
  },
  search(params: TaskSearchRequest) {
    return apiClient.get<ApiResponse<TaskSearchResponse['data']>>('/tasks/search', { params })
  },
}

export const commentApi = {
  create(taskId: string, data: CommentCreateRequest) {
    return apiClient.post<ApiResponse<CommentItem>>(`/tasks/${taskId}/comments`, data)
  },
  list(taskId: string, params?: { page?: number; page_size?: number; order_by?: string }) {
    return apiClient.get<PaginatedResponse<CommentItem>>(`/tasks/${taskId}/comments`, { params })
  },
  update(commentId: string, data: CommentCreateRequest) {
    return apiClient.patch<ApiResponse<CommentItem>>(`/comments/${commentId}`, data)
  },
  delete(commentId: string) {
    return apiClient.delete<ApiResponse<null>>(`/comments/${commentId}`)
  },
}

export const attachmentApi = {
  upload(taskId: string, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post<ApiResponse<AttachmentCreateResponse>>(`/tasks/${taskId}/attachments`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  download(attachmentId: string) {
    window.open(`/api/attachments/${attachmentId}/download`, '_blank')
  },
  delete(attachmentId: string) {
    return apiClient.delete<ApiResponse<null>>(`/attachments/${attachmentId}`)
  },
}

export const dependencyApi = {
  create(taskId: string, data: DependencyCreateRequest) {
    return apiClient.post<ApiResponse<{ id: string; task_id: string; predecessor_id: string; created_at: string }>>(`/tasks/${taskId}/depend`, data)
  },
  list(taskId: string, type?: 'predecessors' | 'successors') {
    return apiClient.get<ApiResponse<TaskBrief[]>>(`/tasks/${taskId}/depend`, { params: { type } })
  },
  delete(taskId: string, targetId: string) {
    return apiClient.delete<ApiResponse<null>>(`/tasks/${taskId}/depend/${targetId}`)
  },
}
