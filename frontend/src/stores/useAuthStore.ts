/**
 * 认证状态管理
 * 处理登录、注册、Token 管理、用户信息
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  RegisterRequest,
  LoginRequest,
  UserProfile,
  TokensResponse,
  ChangePasswordRequest,
  UpdateProfileRequest,
} from '@/types/api'
import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  // ==================== 状态 ====================
  const user = ref<UserProfile | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ==================== 计算属性 ====================
  const isAuthenticated = computed(() => !!accessToken.value)
  const currentUser = computed(() => user.value)
  const displayName = computed(() => user.value?.display_name || user.value?.username || '')
  const userRole = computed(() => user.value?.role || 'member')

  // ==================== 方法 ====================

  /**
   * 初始化：从 localStorage 恢复登录状态
   */
  function init() {
    const storedToken = localStorage.getItem('access_token')
    const storedRefresh = localStorage.getItem('refresh_token')
    if (storedToken) {
      accessToken.value = storedToken
      refreshToken.value = storedRefresh
      fetchCurrentUser()
    }
  }

  /**
   * 用户注册
   */
  async function register(data: RegisterRequest) {
    loading.value = true
    error.value = null
    try {
      const res = await authApi.register(data)
      if (res.data?.tokens) {
        setTokens(res.data.tokens)
      }
      if (res.data?.user) {
        user.value = res.data.user
      }
      return res
    } catch (e: any) {
      error.value = e.message || '注册失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 用户登录
   */
  async function login(data: LoginRequest) {
    loading.value = true
    error.value = null
    try {
      const res = await authApi.login(data)
      if (res.data?.tokens) {
        setTokens(res.data.tokens)
      }
      if (res.data?.user) {
        user.value = res.data.user
      }
      return res
    } catch (e: any) {
      error.value = e.message || '登录失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 刷新 Token
   */
  async function refresh() {
    if (!refreshToken.value) return false
    try {
      const res = await authApi.refresh({ refresh_token: refreshToken.value })
      if (res.data) {
        setTokens(res.data)
        return true
      }
      return false
    } catch {
      logout()
      return false
    }
  }

  /**
   * 获取当前用户信息
   */
  async function fetchCurrentUser() {
    if (!accessToken.value) return
    try {
      const res = await authApi.me() as any
      if (res?.data?.user) {
        user.value = res.data.user
      } else if (res?.data) {
        user.value = res.data
      }
    } catch {
    }
  }

  /**
   * 更新用户资料
   */
  async function updateProfile(data: UpdateProfileRequest) {
    loading.value = true
    try {
      const res = await authApi.updateProfile(data)
      if (res.data) {
        user.value = res.data
      }
      return res
    } finally {
      loading.value = false
    }
  }

  /**
   * 修改密码
   */
  async function changePassword(data: ChangePasswordRequest) {
    loading.value = true
    error.value = null
    try {
      const res = await authApi.changePassword(data)
      return res
    } catch (e: any) {
      error.value = e.message || '密码修改失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 登出
   */
  async function logout() {
    try {
      if (refreshToken.value) {
        await authApi.logout({ refresh_token: refreshToken.value })
      }
    } catch {
      // 忽略登出错误
    } finally {
      clearTokens()
      user.value = null
    }
  }

  /**
   * 清除 Token 并重置状态
   */
  function clearTokens() {
    accessToken.value = null
    refreshToken.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  /**
   * 设置 Token 并持久化
   */
  function setTokens(tokens: TokensResponse) {
    accessToken.value = tokens.access_token
    refreshToken.value = tokens.refresh_token
    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)
  }

  // 初始化时尝试恢复登录状态
  init()

  return {
    // 状态
    user,
    accessToken,
    loading,
    error,
    // 计算属性
    isAuthenticated,
    currentUser,
    displayName,
    userRole,
    // 方法
    register,
    login,
    refresh,
    fetchCurrentUser,
    updateProfile,
    changePassword,
    logout,
    clearTokens,
  }
})
