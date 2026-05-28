import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => {
    const { code, message } = response.data
    if (code !== 0) {
      const error = new Error(message || 'Request failed')
      ;(error as any).errors = response.data.errors
      return Promise.reject(error)
    }
    return response.data
  },
  (error) => {
    const responseData = error.response?.data

    if (responseData?.message || responseData?.code) {
      const normalizedError = new Error(responseData.message || error.message || 'Request failed')
      ;(normalizedError as any).code = responseData.code
      ;(normalizedError as any).details = responseData.details
      ;(normalizedError as any).status = error.response?.status

      if (error.response?.status === 401) {
        const currentPath = window.location.pathname
        if (currentPath !== '/login' && currentPath !== '/register') {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
      return Promise.reject(normalizedError)
    }
    if (error.response?.status === 401) {
      const currentPath = window.location.pathname
      if (currentPath !== '/login' && currentPath !== '/register') {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)
