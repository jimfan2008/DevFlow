<template>
  <div class="chat-view">
    <div class="chat-view__sidebar">
      <div class="chat-view__sidebar-header">
        <h3>群聊与会议</h3>
        <el-button type="primary" size="small" :icon="Plus" @click="showCreateDialog = true">新建</el-button>
      </div>
      <div class="chat-view__group-list">
        <div
          v-for="group in groups"
          :key="group.id"
          :class="['chat-view__group-item', { active: currentGroupId === group.id }]"
          @click="handleSelectGroup(group)"
        >
          <div class="chat-view__group-name">{{ group.name }}</div>
          <div class="chat-view__group-meta">
            <el-tag size="small" :type="group.mode === 'meeting' ? 'warning' : 'info'">
              {{ group.mode === 'meeting' ? '会议' : '讨论' }}
            </el-tag>
            <span v-if="group.members?.length" class="chat-view__group-member-count">{{ group.members.length }} 人</span>
            <span class="chat-view__group-time">{{ formatDate(group.created_at) }}</span>
          </div>
        </div>
        <div v-if="groups.length === 0" class="chat-view__empty-sidebar">
          <p>暂无群组</p>
          <el-button type="primary" size="small" @click="showCreateDialog = true">创建第一个群组</el-button>
        </div>
      </div>
    </div>

    <div v-if="currentGroup" class="chat-view__main">
      <MemberList />
      <div class="chat-view__chat-area">
        <div class="chat-view__messages" ref="messagesRef">
          <MessageItem
            v-for="msg in currentMessages"
            :key="msg.id"
            :message="msg"
            :agent-status="chatStore.getAgentStatus(currentGroupId, msg.sender)"
            :is-current-speaker="meetingState?.currentSpeaker === msg.sender"
          />
        </div>

        <div class="chat-view__input-area">
          <div class="chat-view__input-wrapper">
            <div v-if="showMentions && mentionCandidates.length > 0" class="chat-view__mention-list">
              <div
                v-for="member in mentionCandidates"
                :key="member"
                class="chat-view__mention-item"
                @click="selectMention(member)"
              >@{{ member }}</div>
            </div>
            <el-input
              ref="inputRef"
              v-model="inputMessage"
              :rows="2"
              type="textarea"
              :placeholder="inputPlaceholder"
              :disabled="sending"
              @input="handleInput"
              @keydown.enter.prevent="handleSend"
            />
            <el-button type="primary" :loading="sending" :disabled="!inputMessage.trim()" @click="handleSend">
              {{ meetingState?.isActive ? '发送指令' : '发送' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="chat-view__placeholder">
      <el-empty description="选择或创建一个群组开始聊天" />
    </div>

    <CreateGroupModal
      v-if="showCreateDialog"
      v-model:visible="showCreateDialog"
      @created="handleGroupCreated"
    />

    <MeetingControls
      v-if="showMeetingModal"
      :group-id="currentGroupId"
      :members="currentGroup?.members || []"
      @close="showMeetingModal = false"
      @start="handleStartMeeting"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import { useTasksStore } from '@/stores/tasks'
import { useProfilesStore } from '@/stores/profiles'
import { useWebSocket } from '@/composables/useWebSocket'
import { apiClient } from '@/api'
import MessageItem from '@/components/MessageItem.vue'
import MemberList from '@/components/MemberList.vue'
import MeetingControls from '@/components/MeetingControls.vue'
import CreateGroupModal from '@/components/CreateGroupModal.vue'
import type { GroupInfo, MeetingAgendaItem, MeetingOutcome, TaskItem } from '@/types'

const chatStore = useChatStore()
const tasksStore = useTasksStore()
const profilesStore = useProfilesStore()
const ws = useWebSocket()

const groups = ref<GroupInfo[]>([])
const currentGroupId = ref('')
const currentGroup = ref<GroupInfo | null>(null)
const inputMessage = ref('')
const sending = ref(false)
const showCreateDialog = ref(false)
const showMeetingModal = ref(false)
const showMentions = ref(false)
const mentionCandidates = ref<string[]>([])
const messagesRef = ref<HTMLElement | null>(null)

const currentMessages = computed(() => chatStore.getMessages(currentGroupId.value))
const meetingState = computed(() => chatStore.getMeetingState(currentGroupId.value))
const meetingOutcomes = computed(() => tasksStore.getMeetingOutcomes(currentGroupId.value))
const groupTasks = computed(() => tasksStore.getTasks(currentGroupId.value))

const inputPlaceholder = computed(() => {
  if (!currentGroup.value) return '输入消息...'
  return meetingState.value?.isActive
    ? '输入指令与主持人互动（如：增加自由辩论环节、建议调整议程等）...'
    : '输入消息... 使用 @ 提及成员'
})

onMounted(async () => {
  await fetchGroups()
  profilesStore.fetchProfiles()
  ws.connect()

  ws.on('subscribed', (data: any) => {
    if (data.group_id) {
      chatStore.fetchMessages(data.group_id)
    }
  })

  ws.on('message_new', (data: any) => {
    if (data.message) {
      chatStore.addMessage(data.group_id, data.message)
      scrollToBottom()
    }
  })

  ws.on('message_start', (data: any) => {
    if (data.group_id && data.message_id && data.profile_name) {
      chatStore.startStreamingMessage(data.group_id, data.profile_name, data.message_id)
      chatStore.setAgentStatus(data.group_id, data.profile_name, 'typing')
    }
  })

  ws.on('message_chunk', (data: any) => {
    if (data.group_id && data.profile_name && data.content) {
      chatStore.updateStreamingMessage(data.group_id, data.profile_name, data.content, data.message_id)
      scrollToBottom()
    }
  })

  ws.on('message_complete', (data: any) => {
    if (data.group_id && data.profile_name) {
      chatStore.finalizeStreamingMessage(data.group_id, data.profile_name, data.message_id)
      chatStore.setAgentStatus(data.group_id, data.profile_name, 'idle')
    }
  })

  ws.on('agent_status', (data: any) => {
    if (data.group_id && data.profile_name && data.status) {
      chatStore.setAgentStatus(data.group_id, data.profile_name, data.status)
    }
  })

  ws.on('agent_error', (data: any) => {
    if (data.profile_name) {
      ElMessage.error(`Agent ${data.profile_name} 出错: ${data.error}`)
    }
  })

  ws.on('meeting_started', (data: any) => {
    if (data.group_id) {
      chatStore.startMeetingState(data.group_id, data.topic, data.host_agent, data.participants || [])
      updateGroup(data.group_id, { mode: 'meeting', host_agent: data.host_agent })
      ElMessage.success(`会议「${data.topic}」已开始`)
    }
  })

  ws.on('meeting_phase', (data: any) => {
    if (data.group_id) {
      chatStore.setMeetingPhase(data.group_id, data.phase)
    }
  })

  ws.on('meeting_agenda', (data: any) => {
    if (data.group_id && data.agenda) {
      chatStore.setMeetingAgenda(data.group_id, data.agenda as MeetingAgendaItem[])
    }
  })

  ws.on('meeting_agenda_item', (data: any) => {
    if (data.data) {
      try {
        const info = typeof data.data === 'string' ? JSON.parse(data.data) : data.data
        chatStore.setMeetingAgendaIndex(data.group_id, info.index)
      } catch {}
    }
  })

  ws.on('meeting_grant_speak', (data: any) => {
    if (data.group_id && data.speaker) {
      chatStore.setMeetingCurrentSpeaker(data.group_id, data.speaker)
    }
  })

  ws.on('meeting_minutes', (data: any) => {
    if (data.group_id && data.minutes) {
      chatStore.endMeetingState(data.group_id)
    }
  })

  ws.on('meeting_stopped', (data: any) => {
    if (data.group_id) {
      chatStore.endMeetingState(data.group_id)
      updateGroup(data.group_id, { mode: 'discussion', host_agent: undefined })
      ElMessage.info('会议已结束')
    }
  })

  ws.on('meeting_outcome_saved', (data: any) => {
    if (data.meeting_outcome) {
      tasksStore.addMeetingOutcome(data.group_id, data.meeting_outcome as MeetingOutcome)
    }
  })

  ws.on('task_created', (data: any) => {
    if (data.group_id && data.task) {
      tasksStore.addTask(data.group_id, data.task as TaskItem)
    }
  })
})

onUnmounted(() => {
  if (currentGroupId.value) {
    ws.unsubscribe(currentGroupId.value)
  }
})

async function fetchGroups() {
  try {
    const res = await apiClient.get('/groups') as any
    const data = res?.data?.groups || res?.data || res
    if (Array.isArray(data)) {
      groups.value = data
    } else if (Array.isArray(res?.groups)) {
      groups.value = res.groups
    }
  } catch (e) {
    console.error('Error fetching groups:', e)
  }
}

function handleSelectGroup(group: GroupInfo) {
  if (currentGroupId.value) {
    ws.unsubscribe(currentGroupId.value)
  }
  currentGroupId.value = group.id
  currentGroup.value = group
  ws.subscribe(group.id)

  Promise.all([
    chatStore.fetchMessages(group.id),
    tasksStore.fetchMeetingOutcomes(group.id),
    tasksStore.fetchTasks(group.id),
  ])
}

function handleInput() {
  const text = inputMessage.value
  const lastAtIndex = text.lastIndexOf('@')

  if (lastAtIndex !== -1 && (lastAtIndex === text.length - 1 || !text.slice(lastAtIndex + 1).includes(' '))) {
    const query = text.slice(lastAtIndex + 1).toLowerCase()
    mentionCandidates.value = (currentGroup.value?.members || []).filter(m =>
      m.toLowerCase().includes(query)
    )
    showMentions.value = mentionCandidates.value.length > 0
  } else {
    showMentions.value = false
    mentionCandidates.value = []
  }
}

function selectMention(member: string) {
  const text = inputMessage.value
  const lastAtIndex = text.lastIndexOf('@')
  if (lastAtIndex !== -1) {
    inputMessage.value = text.slice(0, lastAtIndex + 1) + member + ' '
  }
  showMentions.value = false
}

async function handleSend() {
  const content = inputMessage.value.trim()
  if (!content || !currentGroupId.value || sending.value) return

  inputMessage.value = ''
  sending.value = true

  try {
    if (meetingState.value?.isActive) {
      ws.sendIntervention(currentGroupId.value, content)
    } else {
      ws.sendMessage(currentGroupId.value, content)
    }
  } finally {
    sending.value = false
  }
}

function handleStartMeeting(data: { topic: string; hostAgent: string; meetingType: string; durationMinutes: number; preMaterials: string }) {
  if (!currentGroupId.value) return
  ws.startMeeting(currentGroupId.value, data.topic, data.hostAgent, {
    meeting_type: data.meetingType,
    duration_minutes: data.durationMinutes,
    pre_materials: data.preMaterials,
  })
  showMeetingModal.value = false
}

function handleGroupCreated(group: GroupInfo) {
  groups.value.unshift(group)
  handleSelectGroup(group)
}

function updateGroup(groupId: string, updates: Partial<GroupInfo>) {
  const idx = groups.value.findIndex(g => g.id === groupId)
  if (idx >= 0) {
    groups.value[idx] = { ...groups.value[idx], ...updates }
  }
  if (currentGroup.value?.id === groupId) {
    currentGroup.value = { ...currentGroup.value, ...updates }
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('zh-CN')
}
</script>

<style lang="scss" scoped>
.chat-view {
  display: flex;
  height: calc(100vh - #{$header-height} - #{$spacing-6 * 2});

  &__sidebar {
    width: 280px;
    border-right: 1px solid $border-color-light;
    display: flex;
    flex-direction: column;
    background: $bg-color-card;

    &-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: $spacing-3 $spacing-4;
      border-bottom: 1px solid $border-color-light;
      h3 { margin: 0; font-size: $font-size-md; }
    }
  }

  &__group-list {
    flex: 1;
    overflow-y: auto;
    padding: $spacing-2;
  }

  &__group-item {
    padding: $spacing-3;
    border-radius: $radius-md;
    cursor: pointer;
    margin-bottom: $spacing-1;
    transition: background 0.2s;
    &:hover { background: $bg-color-body; }
    &.active { background: $primary-color-light-9; }
  }

  &__group-name {
    font-weight: $font-weight-medium;
    font-size: $font-size-base;
    margin-bottom: $spacing-1;
  }

  &__group-meta {
    display: flex;
    align-items: center;
    gap: $spacing-2;
  }

  &__group-member-count {
    font-size: $font-size-xs;
    color: $text-color-secondary;
  }

  &__group-time {
    font-size: $font-size-xs;
    color: $text-color-placeholder;
  }

  &__empty-sidebar {
    text-align: center;
    padding: $spacing-8 $spacing-4;
    color: $text-color-placeholder;
  }

  &__main {
    flex: 1;
    display: flex;
    min-width: 0;
  }

  &__chat-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  &__messages {
    flex: 1;
    overflow-y: auto;
    padding: $spacing-4;
    display: flex;
    flex-direction: column;
    gap: $spacing-3;
  }

  &__input-area {
    border-top: 1px solid $border-color-light;
    padding: $spacing-3 $spacing-4;
    background: $bg-color-card;
  }

  &__input-wrapper {
    position: relative;
    display: flex;
    gap: $spacing-2;
    align-items: flex-end;
  }

  &__mention-list {
    position: absolute;
    bottom: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 1px solid $border-color-light;
    border-radius: $radius-md;
    box-shadow: $shadow-lg;
    max-height: 200px;
    overflow-y: auto;
    z-index: 100;
  }

  &__mention-item {
    padding: $spacing-2 $spacing-3;
    cursor: pointer;
    font-size: $font-size-sm;
    transition: background 0.15s;
    &:hover { background: $primary-color-light-9; }
  }

  &__placeholder {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}
</style>