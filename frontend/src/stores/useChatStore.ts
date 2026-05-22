import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ChatGroup, ChatMessage as ChatMsg, Meeting, MeetingMinutes } from '@/types/api'
import { chatApi } from '@/api'

export const useChatStore = defineStore('chat', () => {
  const groups = ref<ChatGroup[]>([])
  const currentGroup = ref<ChatGroup | null>(null)
  const messages = ref<ChatMsg[]>([])
  const currentMeeting = ref<Meeting | null>(null)
  const meetingMinutes = ref<MeetingMinutes | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchGroups(page = 1) {
    loading.value = true
    error.value = null
    try {
      const res = await chatApi.groups({ page, page_size: 20 }) as any
      if (res?.data?.groups) {
        groups.value = res.data.groups
      }
    } catch (e: any) {
      error.value = e.message || '获取群组列表失败'
    } finally {
      loading.value = false
    }
  }

  async function createGroup(data: { name: string; members?: string[]; project_id?: string }) {
    loading.value = true
    error.value = null
    try {
      const res = await chatApi.createGroup(data) as any
      const groupData = res?.data?.group || res?.data
      if (groupData) {
        groups.value.unshift(groupData)
        currentGroup.value = groupData
        return groupData
      }
    } catch (e: any) {
      error.value = e.message || '创建群组失败'
    } finally {
      loading.value = false
    }
    return null
  }

  async function fetchGroupDetail(groupId: string) {
    loading.value = true
    try {
      const res = await chatApi.groupDetail(groupId) as any
      if (res?.data?.group) {
        currentGroup.value = res.data.group
      }
    } catch (e: any) {
      error.value = e.message || '获取群组详情失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchMessages(groupId: string) {
    try {
      const res = await chatApi.messages(groupId) as any
      if (res?.data?.messages) {
        messages.value = res.data.messages
      }
    } catch (e: any) {
      error.value = e.message || '获取消息失败'
    }
  }

  async function sendMessage(groupId: string, content: string, mentions?: string[]) {
    try {
      const res = await chatApi.sendMessage(groupId, { content, mentions }) as any
      if (res?.data?.message) {
        messages.value.push(res.data.message)
      }
    } catch (e: any) {
      error.value = e.message || '发送消息失败'
    }
  }

  async function startMeeting(groupId: string, agenda?: string[]) {
    loading.value = true
    try {
      const res = await chatApi.startMeeting(groupId, { agenda }) as any
      if (res?.data?.meeting) {
        currentMeeting.value = res.data.meeting
        return res.data.meeting
      }
      if (res?.data?.group_id) {
        currentMeeting.value = { id: res.data.group_id, mode: res.data.mode } as any
        return res.data
      }
    } catch (e: any) {
      error.value = e.message || '启动会议失败'
    } finally {
      loading.value = false
    }
    return null
  }

  async function endMeeting(groupId: string) {
    loading.value = true
    try {
      const res = await chatApi.endMeeting(groupId) as any
      if (res?.data?.outcome) {
        meetingMinutes.value = res.data.outcome as any
        currentMeeting.value = null
      }
    } catch (e: any) {
      error.value = e.message || '结束会议失败'
    } finally {
      loading.value = false
    }
  }

  return {
    groups,
    currentGroup,
    messages,
    currentMeeting,
    meetingMinutes,
    loading,
    error,
    fetchGroups,
    createGroup,
    fetchGroupDetail,
    fetchMessages,
    sendMessage,
    startMeeting,
    endMeeting,
  }
})
