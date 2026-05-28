/**
 * WebSocket 状态管理
 * 管理 WebSocket 连接、消息收发、实时通知推送
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { InboxNotification } from '@/types/api'

export const useWebSocketStore = defineStore('websocket', () => {
  // ==================== 状态 ====================
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const isConnecting = ref(false)
  const lastMessage = ref<InboxNotification | null>(null)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000 // 3秒后重连

  // 存储所有收到的消息（用于调试和展示）
  const messageHistory = ref<Array<{ type: string; data: any; time: string }>>([])
  const notificationCallback = ref<((notification: InboxNotification) => void) | null>(null)

  // ==================== 配置 ====================
  const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL || ''

  // ==================== 计算属性 ====================
  const connectionStatus = computed(() => {
    if (isConnecting.value) return 'connecting'
    if (isConnected.value) return 'connected'
    return 'disconnected'
  })

  const connectionStatusLabel = computed(() => ({
    connected: '已连接',
    connecting: '连接中...',
    disconnected: '未连接',
  }))

  // ==================== 方法 ====================

  /**
   * 建立 WebSocket 连接
   */
  function connect(token: string) {
    if (isConnected.value || isConnecting.value) return

    isConnecting.value = true
    const base = wsBaseUrl || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
    const wsUrl = `${base}/ws/notifications?token=${encodeURIComponent(token)}`

    try {
      ws.value = new WebSocket(wsUrl)

      ws.value.onopen = () => {
        isConnected.value = true
        isConnecting.value = false
        reconnectAttempts.value = 0
        addMessage('connected', { url: wsUrl })
        console.log('[WebSocket] 连接已建立')
      }

      ws.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          addMessage(data.type || 'notification', data.data)

          // 通知类型消息 - 推送实时通知
          if (data.type === 'notification' && data.data) {
            const notification: InboxNotification = {
              id: data.data.id || String(Date.now()),
              user_id: data.data.user_id || '',
              type: data.data.type,
              title: data.data.title || '',
              body: data.data.body || '',
              task_id: data.data.task_id,
              board_id: data.data.board_id,
              actor: data.data.actor || { id: '', username: '', display_name: '' },
              is_read: false,
              created_at: data.data.created_at || new Date().toISOString(),
            }
            lastMessage.value = notification
            if (notificationCallback.value) {
              notificationCallback.value(notification)
            }
          }
        } catch (e) {
          console.error('[WebSocket] 消息解析失败:', e)
        }
      }

      ws.value.onerror = (error) => {
        console.error('[WebSocket] 连接错误:', error)
        addMessage('error', { message: '连接错误' })
      }

      ws.value.onclose = (event) => {
        isConnected.value = false
        isConnecting.value = false
        addMessage('closed', { code: event.code, reason: event.reason })
        console.log(`[WebSocket] 连接关闭: ${event.code} ${event.reason}`)

        // 尝试重连
        attemptReconnect()
      }
    } catch (e) {
      isConnecting.value = false
      console.error('[WebSocket] 连接异常:', e)
    }
  }

  /**
   * 尝试重连
   */
  function attemptReconnect() {
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      console.log('[WebSocket] 达到最大重连次数，停止重连')
      return
    }

    reconnectAttempts.value++
    console.log(`[WebSocket] 第 ${reconnectAttempts.value} 次重连...`)

    setTimeout(() => {
      // 如果已有连接则先关闭
      if (ws.value) {
        ws.value.close()
      }
      // 需要 token 才能重连，这里由外部调用 connect(token)
      // 此方法仅用于内部状态管理
    }, reconnectDelay)
  }

  /**
   * 发送消息
   */
  function send(message: string | object) {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      console.warn('[WebSocket] 连接未打开，无法发送消息')
      return false
    }
    const payload = typeof message === 'string' ? message : JSON.stringify(message)
    ws.value.send(payload)
    addMessage('sent', message)
    return true
  }

  /**
   * 注册通知回调
   */
  function onNotification(callback: (notification: InboxNotification) => void) {
    notificationCallback.value = callback
  }

  /**
   * 移除通知回调
   */
  function removeNotificationCallback() {
    notificationCallback.value = null
  }

  /**
   * 关闭连接
   */
  function disconnect() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    isConnected.value = false
    isConnecting.value = false
    reconnectAttempts.value = 0
    addMessage('disconnect', {})
  }

  /**
   * 记录消息历史
   */
  function addMessage(type: string, data: any) {
    messageHistory.value.push({
      type,
      data,
      time: new Date().toISOString(),
    })
    // 限制历史记录长度
    if (messageHistory.value.length > 100) {
      messageHistory.value = messageHistory.value.slice(-50)
    }
  }

  /**
   * 清空消息历史
   */
  function clearHistory() {
    messageHistory.value = []
  }

  // ==================== 生命周期 ====================
  // 页面关闭时断开连接
  if (typeof window !== 'undefined') {
    window.addEventListener('beforeunload', () => {
      disconnect()
    })
  }

  return {
    // 状态
    ws,
    isConnected,
    isConnecting,
    lastMessage,
    reconnectAttempts,
    messageHistory,
    // 计算属性
    connectionStatus,
    connectionStatusLabel,
    // 方法
    connect,
    attemptReconnect,
    send,
    onNotification,
    removeNotificationCallback,
    disconnect,
    clearHistory,
  }
})
