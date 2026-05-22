import { apiClient } from '../client'
import type { ApiResponse, TokensResponse, UserProfile, RegisterRequest, LoginRequest, ChangePasswordRequest, UpdateProfileRequest } from '../../types/api'

export const authApi = {
  register(data: RegisterRequest) {
    return apiClient.post<ApiResponse<{ user: UserProfile; tokens: TokensResponse }>>('/auth/register', data)
  },
  login(data: LoginRequest) {
    return apiClient.post<ApiResponse<{ user: UserProfile; tokens: TokensResponse }>>('/auth/login', data)
  },
  refresh(data: { refresh_token: string }) {
    return apiClient.get<ApiResponse<TokensResponse>>('/auth/refresh', { params: { token: data.refresh_token } })
  },
  me() {
    return apiClient.get<ApiResponse<UserProfile>>('/auth/me')
  },
  updateProfile(data: UpdateProfileRequest) {
    return apiClient.patch<ApiResponse<UserProfile>>('/auth/me', data)
  },
  changePassword(data: ChangePasswordRequest) {
    return apiClient.post<ApiResponse<null>>('/auth/change-password', data)
  },
  logout(data?: { refresh_token: string }) {
    return apiClient.post<ApiResponse<null>>('/auth/logout', data)
  },
}
