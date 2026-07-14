<template>
  <div class="chat-view">
    <div class="chat-view__sidebar" :class="{ collapsed: sidebarCollapsed }">
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
          <div class="chat-view__group-name-row">
            <span class="chat-view__group-name">{{ group.name }}</span>
            <el-button
              type="danger"
              size="small"
              :icon="Delete"
              circle
              text
              class="chat-view__group-delete"
              @click.stop="handleDeleteGroup(group)"
            />
          </div>
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

    <el-button
      text
      size="small"
      :icon="sidebarCollapsed ? Expand : Fold"
      class="chat-view__sidebar-toggle"
      @click="sidebarCollapsed = !sidebarCollapsed"
    />
    <div v-if="currentGroup" class="chat-view__main">
      <div class="member-list-wrap" :class="{ collapsed: memberListCollapsed }">
        <div class="member-list-toggle">
          <span class="member-list-toggle__title">成员</span>
        </div>
        <MemberList />
      </div>
      <el-button
        text
        size="small"
        :icon="memberListCollapsed ? Expand : Fold"
        class="chat-view__member-toggle"
        @click="memberListCollapsed = !memberListCollapsed"
      />
      <div class="chat-view__chat-area">
        <div class="chat-view__messages" ref="messagesRef" @scroll="onMessagesScroll">
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
import { Plus, Delete, Fold, Expand } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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
const sidebarCollapsed = ref(false)
const memberListCollapsed = ref(false)
const showMentions = ref(false)
const mentionCandidates = ref<string[]>([])
const messagesRef = ref<HTMLElement | null>(null)
const isNearBottom = ref(true)
const loadingHistory = ref(false)

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
      chatStore.removeTempMessages(data.group_id, data.message.content, data.message.sender)
      chatStore.addMessage(data.group_id, data.message)
      if (isNearBottom.value) scrollToBottom()
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
      if (isNearBottom.value) scrollToBottom()
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
  ]).then(() => {
    scrollToBottom()
  })
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

function _tempId() {
  return 'tmp_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8)
}

async function handleSend() {
  const content = inputMessage.value.trim()
  if (!content || !currentGroupId.value || sending.value) return

  inputMessage.value = ''
  sending.value = true

  const tempId = _tempId()
  chatStore.addMessage(currentGroupId.value, {
    id: tempId,
    group_id: currentGroupId.value,
    sender: 'user',
    role: 'user',
    content,
    timestamp: new Date().toISOString(),
    is_streaming: false,
  })

  scrollToBottom()

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

async function handleDeleteGroup(group: GroupInfo) {
  try {
    await ElMessageBox.confirm(
      `确定要删除群组「${group.name}」吗？此操作不可撤销。`,
      '删除群组',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return // 用户取消
  }

  try {
    await apiClient.delete(`/groups/${group.id}`)
    ElMessage.success('群组已删除')

    // 从本地列表中移除
    const idx = groups.value.findIndex(g => g.id === group.id)
    if (idx >= 0) groups.value.splice(idx, 1)

    // 如果删除的是当前选中的群，清除所有相关状态
    if (currentGroupId.value === group.id) {
      ws.unsubscribe(group.id)
      chatStore.clearMessages(group.id)
      chatStore.clearMeetingState(group.id)
      // 清理 tasks store 中的相关数据
      delete (tasksStore.meetingOutcomes as any)[group.id]
      delete (tasksStore.tasks as any)[group.id]
      currentGroupId.value = ''
      currentGroup.value = null
    }
  } catch (e: any) {
    ElMessage.error(e.message || '删除群组失败')
  }
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

function onMessagesScroll() {
  const el = messagesRef.value
  if (!el) return
  const threshold = 100
  isNearBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < threshold
  if (el.scrollTop < 50 && chatStore.hasMoreMessages(currentGroupId.value) && !chatStore.isLoadingMessages(currentGroupId.value)) {
    const prevHeight = el.scrollHeight
    chatStore.loadMoreMessages(currentGroupId.value).then(() => {
      nextTick(() => {
        if (messagesRef.value) {
          messagesRef.value.scrollTop = messagesRef.value.scrollHeight - prevHeight
        }
      })
    })
  }
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('zh-CN')
}
</script>

<style lang="scss" scoped>
.chat-view {
  display: flex;
  height: calc(100vh - #{$global-nav-height} - #{$spacing-section});

  &__sidebar {
    width: 280px;
    border-right: 1px solid $hairline;
    display: flex;
    flex-direction: column;
    background: $canvas;
    overflow: hidden;
    transition: width 0.25s ease;

    &.collapsed {
      width: 0;
      min-width: 0;
    }

    &-header {
      display: flex;
      align-items: center;
      gap: $spacing-xs;
      padding: $spacing-sm $spacing-4;
      border-bottom: 1px solid $hairline;
      white-space: nowrap;
      h3 {
        margin: 0;
        font-family: $font-text;
        font-size: $body-strong-size;
        font-weight: $body-strong-weight;
        letter-spacing: $body-strong-tracking;
      }
    }
  }

  &__group-list {
    flex: 1;
    overflow-y: auto;
    padding: $spacing-xs;
  }

  &__group-item {
    padding: $spacing-sm;
    border-radius: $radius-sm;
    cursor: pointer;
    margin-bottom: $spacing-xxs;
    transition: background 0.15s;
    &:hover { background: $canvas-parchment; }
    &.active { background: rgba($primary, 0.08); }
  }

  &__group-name-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-xxs;
  }

  &__group-name {
    font-family: $font-text;
    font-weight: $body-strong-weight;
    font-size: $body-size;
    letter-spacing: $body-tracking;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__group-delete {
    margin-left: $spacing-xxs;
    opacity: 0;
    transition: opacity 0.15s;
    flex-shrink: 0;
  }

  &__group-item:hover &__group-delete {
    opacity: 1;
  }

  &__group-meta {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
  }

  &__group-member-count {
    font-size: $fine-print-size;
    color: $ink-muted-48;
  }

  &__group-time {
    font-size: $fine-print-size;
    color: $ink-muted-48;
  }

  &__empty-sidebar {
    text-align: center;
    padding: $spacing-xl $spacing-4;
    color: $ink-muted-48;
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
    gap: $spacing-sm;
  }

  &__input-area {
    border-top: 1px solid $hairline;
    padding: $spacing-sm $spacing-4;
    background: $canvas;
  }

  &__input-wrapper {
    position: relative;
    display: flex;
    gap: $spacing-xs;
    align-items: flex-end;
  }

  &__mention-list {
    position: absolute;
    bottom: 100%;
    left: 0;
    right: 0;
    background: $canvas;
    border: 1px solid $hairline;
    border-radius: $radius-sm;
    max-height: 200px;
    overflow-y: auto;
    z-index: 100;
  }

  &__mention-item {
    padding: $spacing-xs $spacing-sm;
    cursor: pointer;
    font-size: $caption-size;
    transition: background 0.15s;
    &:hover { background: rgba($primary, 0.08); }
  }

  &__placeholder {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  &__sidebar-toggle {
    flex-shrink: 0;
    align-self: flex-start;
    margin-top: $spacing-xs;
    border-right: 1px solid $hairline;
    border-radius: 0;
    height: 36px;
  }

  &__member-toggle {
    flex-shrink: 0;
    align-self: flex-start;
    margin-top: $spacing-xs;
    border-left: 1px solid $hairline;
    border-radius: 0;
    height: 36px;
  }
}

.member-list-wrap {
  width: 220px;
  overflow: hidden;
  transition: width 0.25s ease;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  border-left: 1px solid $hairline;

  &.collapsed {
    width: 0;
    min-width: 0;
  }
}

.member-list-toggle {
  display: flex;
  align-items: center;
  padding: $spacing-sm $spacing-4;
  border-bottom: 1px solid $hairline;
  white-space: nowrap;

  &__title {
    font-family: $font-text;
    font-size: $body-strong-size;
    font-weight: $body-strong-weight;
    letter-spacing: $body-strong-tracking;
  }
}
</style>