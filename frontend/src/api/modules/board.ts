import { apiClient } from '../client'
import type { ApiResponse, PaginatedResponse, BoardDetail as BoardDetailType, BoardListItem, BoardCreateRequest, BoardUpdateRequest, ColumnCreateRequest, ColumnUpdateRequest, ColumnReorderRequest } from '../../types/api'

export const boardApi = {
  create(data: BoardCreateRequest) {
    return apiClient.post<ApiResponse<BoardDetailType>>('/boards/', data)
  },
  list(params?: { page?: number; page_size?: number; order_by?: string; order_dir?: string }) {
    return apiClient.get<PaginatedResponse<BoardListItem>>('/boards/', { params })
  },
  detail(boardId: string) {
    return apiClient.get<ApiResponse<BoardDetailType>>(`/boards/${boardId}`)
  },
  update(boardId: string, data: BoardUpdateRequest) {
    return apiClient.patch<ApiResponse<BoardDetailType>>(`/boards/${boardId}`, data)
  },
  delete(boardId: string) {
    return apiClient.delete<ApiResponse<null>>(`/boards/${boardId}`)
  },
  createColumn(boardId: string, data: ColumnCreateRequest) {
    return apiClient.post<ApiResponse<{ id: string; board_id: string; name: string; color: string; position: number; is_active: boolean; created_at: string }>>(`/boards/${boardId}/columns`, data)
  },
  updateColumn(boardId: string, columnId: string, data: ColumnUpdateRequest) {
    return apiClient.patch<ApiResponse<{ id: string; name: string; color: string; position: number }>>(`/boards/${boardId}/columns/${columnId}`, data)
  },
  deleteColumn(boardId: string, columnId: string) {
    return apiClient.delete<ApiResponse<null>>(`/boards/${boardId}/columns/${columnId}`)
  },
  reorderColumns(boardId: string, data: ColumnReorderRequest) {
    return apiClient.patch<ApiResponse<{ columns: BoardDetailType['columns'] }>>(`/boards/${boardId}/columns/reorder`, data)
  },
}
