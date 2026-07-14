import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Message, MeetingState, MeetingAgendaItem } from '@/types'
import { apiClient } from '@/api'

const PAGE_SIZE = 30

export const useChatStore = defineStore('chat', () => {
  const messagesMap = ref<Record<string, Message[]>>({})
  const streamingMessages = ref<Record<string, boolean>>({})
  const agentStatuses = ref<Record<string, Record<string, string>>>({})
  const meetingStates = ref<Record<string, MeetingState>>({})

  const messageOffsets = ref<Record<string, number>>({})
  const messageTotals = ref<Record<string, number>>({})
  const messageLoading = ref<Record<string, boolean>>({})

  function getMessages(groupId: string): Message[] {
    return messagesMap.value[groupId] || []
  }

  function hasMoreMessages(groupId: string): boolean {
    const loaded = messageOffsets.value[groupId] || 0
    const total = messageTotals.value[groupId] || 0
    return loaded < total
  }

  function isLoadingMessages(groupId: string): boolean {
    return !!messageLoading.value[groupId]
  }

  function addMessage(groupId: string, message: Message) {
    if (!messagesMap.value[groupId]) {
      messagesMap.value[groupId] = []
    }
    const existing = messagesMap.value[groupId].find(m => m.id === message.id)
    if (!existing) {
      messagesMap.value[groupId].push(message)
    }
  }

  function startStreamingMessage(groupId: string, profileName: string, messageId: string) {
    if (!messagesMap.value[groupId]) {
      messagesMap.value[groupId] = []
    }
    messagesMap.value[groupId].push({
      id: messageId,
      group_id: groupId,
      sender: profileName,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      is_streaming: true,
    })
  }

  function updateStreamingMessage(groupId: string, profileName: string, content: string, messageId?: string) {
    if (!messagesMap.value[groupId]) {
      messagesMap.value[groupId] = []
    }
    let existingMsg = messageId
      ? messagesMap.value[groupId].find(m => m.id === messageId)
      : messagesMap.value[groupId].find(m => m.sender === profileName && m.is_streaming)

    if (existingMsg) {
      existingMsg.content += content
    }
  }

  function finalizeStreamingMessage(groupId: string, profileName: string, messageId?: string) {
    if (!messagesMap.value[groupId]) return
    const msg = messageId
      ? messagesMap.value[groupId].find(m => m.id === messageId)
      : messagesMap.value[groupId].find(m => m.sender === profileName && m.is_streaming)
    if (msg) {
      msg.is_streaming = false
    }
  }

  function setAgentStatus(groupId: string, profileName: string, status: string) {
    if (!agentStatuses.value[groupId]) {
      agentStatuses.value[groupId] = {}
    }
    agentStatuses.value[groupId][profileName] = status
  }

  function getAgentStatus(groupId: string, profileName: string): string {
    return agentStatuses.value[groupId]?.[profileName] || 'idle'
  }

  function removeTempMessages(groupId: string, content: string, sender: string) {
    if (!messagesMap.value[groupId]) return
    messagesMap.value[groupId] = messagesMap.value[groupId].filter(
      m => !(m.id.startsWith('tmp_') && m.content === content && m.sender === sender)
    )
  }

  function clearMessages(groupId: string) {
    messagesMap.value[groupId] = []
    messageOffsets.value[groupId] = 0
    messageTotals.value[groupId] = 0
  }

  function getMeetingState(groupId: string): MeetingState | null {
    return meetingStates.value[groupId] || null
  }

  function startMeetingState(groupId: string, topic: string, hostAgent: string, participants: string[]) {
    meetingStates.value[groupId] = {
      isActive: true,
      topic,
      hostAgent,
      participants,
      agenda: [],
      currentPhase: 'agenda_planning',
      currentSpeaker: null,
      currentAgendaIndex: -1,
      minutes: '',
    }
  }

  function setMeetingAgenda(groupId: string, agenda: MeetingAgendaItem[]) {
    if (meetingStates.value[groupId]) {
      meetingStates.value[groupId].agenda = agenda
    }
  }

  function setMeetingPhase(groupId: string, phase: string) {
    if (meetingStates.value[groupId]) {
      meetingStates.value[groupId].currentPhase = phase
    }
  }

  function setMeetingCurrentSpeaker(groupId: string, speaker: string | null) {
    if (meetingStates.value[groupId]) {
      meetingStates.value[groupId].currentSpeaker = speaker
    }
  }

  function setMeetingAgendaIndex(groupId: string, index: number) {
    if (meetingStates.value[groupId]) {
      meetingStates.value[groupId].currentAgendaIndex = index
    }
  }

  function endMeetingState(groupId: string) {
    if (meetingStates.value[groupId]) {
      meetingStates.value[groupId].isActive = false
    }
  }

  function clearMeetingState(groupId: string) {
    delete meetingStates.value[groupId]
  }

  async function fetchMessages(groupId: string) {
    messageOffsets.value[groupId] = 0
    try {
      const response = await apiClient.get(`/groups/${groupId}/ws-messages`, {
        params: { limit: PAGE_SIZE, offset: 0 }
      }) as any
      const data = response?.data?.messages || []
      messageTotals.value[groupId] = response?.data?.total || data.length
      messageOffsets.value[groupId] = data.length
      if (Array.isArray(data)) {
        messagesMap.value[groupId] = data
      }
    } catch (e) {
      console.error('Error fetching messages:', e)
    }
  }

  async function loadMoreMessages(groupId: string) {
    if (messageLoading.value[groupId]) return
    if (!hasMoreMessages(groupId)) return

    messageLoading.value[groupId] = true
    const currentOffset = messageOffsets.value[groupId] || 0

    try {
      const response = await apiClient.get(`/groups/${groupId}/ws-messages`, {
        params: { limit: PAGE_SIZE, offset: currentOffset }
      }) as any
      const data = response?.data?.messages || []
      messageTotals.value[groupId] = response?.data?.total || 0
      if (Array.isArray(data) && data.length > 0) {
        messagesMap.value[groupId] = [...data, ...(messagesMap.value[groupId] || [])]
        messageOffsets.value[groupId] = currentOffset + data.length
      }
    } catch (e) {
      console.error('Error loading more messages:', e)
    } finally {
      messageLoading.value[groupId] = false
    }
  }

  return {
    messagesMap,
    streamingMessages,
    agentStatuses,
    meetingStates,
    messageOffsets,
    messageTotals,
    messageLoading,
    getMessages,
    hasMoreMessages,
    isLoadingMessages,
    addMessage,
    startStreamingMessage,
    updateStreamingMessage,
    finalizeStreamingMessage,
    setAgentStatus,
    getAgentStatus,
    clearMessages,
    removeTempMessages,
    getMeetingState,
    startMeetingState,
    setMeetingAgenda,
    setMeetingPhase,
    setMeetingCurrentSpeaker,
    setMeetingAgendaIndex,
    endMeetingState,
    clearMeetingState,
    fetchMessages,
    loadMoreMessages,
  }
})