import { ref, onUnmounted } from 'vue'

const WS_BASE = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws`

export function useWebSocket() {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const handlers = new Map<string, Set<(data: any) => void>>()

  function connect() {
    if (ws.value?.readyState === WebSocket.OPEN) return

    ws.value = new WebSocket(WS_BASE)

    ws.value.onopen = () => {
      connected.value = true
    }

    ws.value.onclose = () => {
      connected.value = false
      setTimeout(() => connect(), 3000)
    }

    ws.value.onerror = () => {
      connected.value = false
    }

    ws.value.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data)
        const type = data.type
        const typeHandlers = handlers.get(type)
        if (typeHandlers) {
          typeHandlers.forEach(fn => fn(data))
        }
        const allHandlers = handlers.get('*')
        if (allHandlers) {
          allHandlers.forEach(fn => fn(data))
        }
      } catch (e) {
        console.error('WebSocket message parse error:', e)
      }
    }
  }

  function disconnect() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
      connected.value = false
    }
  }

  function send(data: Record<string, unknown>) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(data))
    }
  }

  function subscribe(groupId: string) {
    send({ type: 'subscribe', group_id: groupId })
  }

  function unsubscribe(groupId: string) {
    send({ type: 'unsubscribe', group_id: groupId })
  }

  function sendMessage(groupId: string, content: string) {
    send({ type: 'send_message', group_id: groupId, content })
  }

  function sendIntervention(groupId: string, content: string) {
    send({ type: 'meeting_intervention', group_id: groupId, content })
  }

  function startMeeting(groupId: string, topic: string, hostAgent: string, options?: Record<string, unknown>) {
    send({
      type: 'start_meeting',
      group_id: groupId,
      topic,
      host_agent: hostAgent,
      ...options,
    })
  }

  function stopMeeting(groupId: string) {
    send({ type: 'stop_meeting', group_id: groupId })
  }

  function on(type: string, handler: (data: any) => void) {
    if (!handlers.has(type)) {
      handlers.set(type, new Set())
    }
    handlers.get(type)!.add(handler)
  }

  function off(type: string, handler: (data: any) => void) {
    const typeHandlers = handlers.get(type)
    if (typeHandlers) {
      typeHandlers.delete(handler)
    }
  }

  onUnmounted(() => {
    disconnect()
    handlers.clear()
  })

  return {
    connected,
    connect,
    disconnect,
    send,
    subscribe,
    unsubscribe,
    sendMessage,
    sendIntervention,
    startMeeting,
    stopMeeting,
    on,
    off,
  }
}