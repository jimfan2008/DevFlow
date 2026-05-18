import { apiClient } from '../client'
import type { ApiResponse, PaginatedResponse, UserListItem, UserDetailResponse } from '../../types/api'

export const userApi = {
  list(params?: { page?: number; page_size?: number }) {
    return apiClient.get<PaginatedResponse<UserListItem>>('/users', { params })
  },
  detail(userId: string) {
    return apiClient.get<ApiResponse<UserDetailResponse>>(`/users/${userId}`)
  },
}
