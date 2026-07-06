import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Message, MeetingState, MeetingAgendaItem } from '@/types'
import { apiClient } from '@/api'

export const useChatStore = defineStore('chat', () => {
  const messagesMap = ref<Record<string, Message[]>>({})
  const streamingMessages = ref<Record<string, boolean>>({})
  const agentStatuses = ref<Record<string, Record<string, string>>>({})
  const meetingStates = ref<Record<string, MeetingState>>({})

  function getMessages(groupId: string): Message[] {
    return messagesMap.value[groupId] || []
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
    try {
      const response = await apiClient.get(`/groups/${groupId}/ws-messages`)
      const data = (response as any)?.data?.messages || (response as any)?.messages
      if (Array.isArray(data)) {
        messagesMap.value[groupId] = data
      }
    } catch (e) {
      console.error('Error fetching messages:', e)
    }
  }

  return {
    messagesMap,
    streamingMessages,
    agentStatuses,
    meetingStates,
    getMessages,
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
  }
})