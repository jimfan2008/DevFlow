<template>
  <div class="chat-view">
    <div class="chat-view__sidebar">
      <div class="chat-view__sidebar-header">
        <h3>群聊与会议</h3>
        <el-button type="primary" size="small" :icon="Plus" @click="showCreateDialog = true">新建</el-button>
      </div>
      <div class="chat-view__group-list">
        <div
          v-for="group in store.groups"
          :key="group.id"
          :class="['chat-view__group-item', { active: currentGroupId === group.id }]"
          @click="handleSelectGroup(group)"
        >
          <div class="chat-view__group-name">{{ group.name }}</div>
          <div class="chat-view__group-meta">
            <el-tag size="small" :type="(group.mode === 'meeting') ? 'warning' : 'info'">{{ (group.mode === 'meeting') ? '会议' : '讨论' }}</el-tag>
            <span class="chat-view__group-time">{{ formatDate(group.created_at) }}</span>
          </div>
        </div>
        <el-empty v-if="store.groups.length === 0" description="暂无群组" :image-size="40" />
      </div>
    </div>

    <div class="chat-view__main" v-if="store.currentGroup">
      <div class="chat-view__main-header">
        <h3>{{ store.currentGroup.name }}</h3>
        <div class="chat-view__main-actions">
          <el-tag size="small">{{ store.currentGroup.mode === 'meeting' ? '会议模式' : '讨论模式' }}</el-tag>
          <el-button v-if="store.currentGroup.mode === 'discussion'" size="small" type="warning" @click="handleStartMeeting">启动会议</el-button>
          <el-button v-if="store.currentMeeting" size="small" type="danger" @click="handleEndMeeting">结束会议</el-button>
        </div>
      </div>

      <div v-if="!store.currentMeeting" class="chat-view__messages" ref="messagesRef">
        <div v-for="msg in store.messages" :key="msg.id" :class="['chat-view__msg', msg.role || msg.type]">
          <div class="chat-view__msg-sender">{{ msg.sender_name || msg.sender || '未知' }}</div>
          <div class="chat-view__msg-content">{{ msg.content }}</div>
          <div class="chat-view__msg-time">{{ formatTime(msg.created_at || msg.timestamp) }}</div>
        </div>
        <div v-if="streamingText" class="chat-view__msg skill_message">
          <div class="chat-view__msg-sender">Agent</div>
          <div class="chat-view__msg-content streaming">{{ streamingText }}<span class="chat-view__cursor">|</span></div>
        </div>
      </div>

      <div v-else class="chat-view__meeting">
        <el-card shadow="never">
          <template #header>会议议程</template>
          <el-timeline>
            <el-timeline-item v-for="(item, idx) in store.currentMeeting.agenda" :key="idx">{{ item }}</el-timeline-item>
          </el-timeline>
        </el-card>
        <el-card shadow="never" style="margin-top: 16px">
          <template #header>会议消息</template>
          <div class="chat-view__messages" ref="messagesRef">
            <div v-for="msg in store.messages" :key="msg.id" :class="['chat-view__msg', msg.role || msg.type]">
              <div class="chat-view__msg-sender">{{ msg.sender_name || msg.sender || '未知' }}</div>
              <div class="chat-view__msg-content">{{ msg.content }}</div>
              <div class="chat-view__msg-time">{{ formatTime(msg.created_at || msg.timestamp) }}</div>
            </div>
          </div>
        </el-card>
        <div v-if="store.meetingMinutes" class="chat-view__minutes">
          <h4>会议纪要</h4>
          <p>{{ store.meetingMinutes.summary }}</p>
          <div v-if="store.meetingMinutes.decisions.length">
            <strong>决议:</strong>
            <ul><li v-for="d in store.meetingMinutes.decisions" :key="d">{{ d }}</li></ul>
          </div>
          <div v-if="store.meetingMinutes.action_items.length">
            <strong>行动项:</strong>
            <ul><li v-for="a in store.meetingMinutes.action_items" :key="a">{{ a }}</li></ul>
          </div>
        </div>
      </div>

      <div class="chat-view__input-area">
        <el-input
          v-model="messageInput"
          type="textarea"
          :rows="2"
          placeholder="输入消息... (@mention 成员, Ctrl+Enter发送)"
          @keyup.enter.ctrl="handleSend"
        />
        <el-button type="primary" :loading="sendLoading" @click="handleSend">发送</el-button>
      </div>
    </div>

    <div v-else class="chat-view__placeholder">
      <el-empty description="选择或创建一个群组开始聊天" />
    </div>

    <el-dialog v-model="showCreateDialog" title="创建群组" width="440px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="群组名称" required>
          <el-input v-model="createForm.name" placeholder="输入群组名称" />
        </el-form-item>
        <el-form-item label="模式">
          <el-radio-group v-model="createForm.mode">
            <el-radio value="discussion">讨论模式</el-radio>
            <el-radio value="meeting">会议模式</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="store.loading" :disabled="!createForm.name.trim()" @click="handleCreateGroup">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/useChatStore'
import { useWebSocketStore } from '@/stores/useWebSocketStore'

const store = useChatStore()
const wsStore = useWebSocketStore()
const currentGroupId = ref('')
const messageInput = ref('')
const sendLoading = ref(false)
const showCreateDialog = ref(false)
const createForm = ref({ name: '', mode: 'discussion' as 'discussion' | 'meeting' })
const messagesRef = ref<HTMLElement | null>(null)
const streamingText = ref('')

onMounted(() => {
  store.fetchGroups()
  wsStore.onNotification((notif: any) => {
    if (notif.type === 'skill_message' && notif.body) {
      streamingText.value += notif.body
      setTimeout(() => { streamingText.value = '' }, 3000)
    }
    if (currentGroupId.value) {
      store.fetchMessages(currentGroupId.value)
    }
  })
})

function handleSelectGroup(group: any) {
  currentGroupId.value = group.id
  store.fetchGroupDetail(group.id)
  store.fetchMessages(group.id)
}

async function handleSend() {
  const content = messageInput.value.trim()
  if (!content || !currentGroupId.value) return
  const mentions = content.match(/@(\w+)/g)?.map(m => m.slice(1)) || []
  sendLoading.value = true
  await store.sendMessage(currentGroupId.value, content, mentions)
  sendLoading.value = false
  messageInput.value = ''
  scrollToBottom()
}

async function handleStartMeeting() {
  if (!currentGroupId.value) return
  const meeting = await store.startMeeting(currentGroupId.value)
  if (meeting) ElMessage.success('会议已启动')
}

async function handleEndMeeting() {
  if (!store.currentMeeting || !currentGroupId.value) return
  await store.endMeeting(currentGroupId.value)
  ElMessage.success('会议已结束，纪要已生成')
}

async function handleCreateGroup() {
  const group = await store.createGroup({ name: createForm.value.name })
  if (group) {
    ElMessage.success('群组创建成功')
    showCreateDialog.value = false
    createForm.value = { name: '', mode: 'discussion' }
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

watch(() => store.messages.length, () => scrollToBottom())

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('zh-CN')
}

function formatTime(d: string) {
  return new Date(d).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
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

  &__group-time {
    font-size: $font-size-xs;
    color: $text-color-placeholder;
  }

  &__main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;

    &-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: $spacing-3 $spacing-4;
      border-bottom: 1px solid $border-color-light;
      h3 { margin: 0; }
    }

    &-actions {
      display: flex;
      align-items: center;
      gap: $spacing-2;
    }
  }

  &__messages {
    flex: 1;
    overflow-y: auto;
    padding: $spacing-4;
    display: flex;
    flex-direction: column;
    gap: $spacing-3;
  }

  &__msg {
    max-width: 70%;
    &.skill_message {
      align-self: flex-start;
      .chat-view__msg-content { background: #f0f9eb; border: 1px solid #e1f3d8; }
    }
    &-sender {
      font-size: $font-size-xs;
      color: $text-color-secondary;
      margin-bottom: 2px;
    }
    &-content {
      background: $primary-color-light-9;
      padding: $spacing-2 $spacing-3;
      border-radius: $radius-lg;
      font-size: $font-size-base;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }
    &-time {
      font-size: $font-size-xs;
      color: $text-color-placeholder;
      margin-top: 2px;
    }
  }

  &__cursor {
    animation: blink 1s infinite;
  }

  &__meeting {
    flex: 1;
    overflow-y: auto;
    padding: $spacing-4;
  }

  &__minutes {
    margin-top: $spacing-4;
    padding: $spacing-4;
    background: #f0f9eb;
    border-radius: $radius-md;
    h4 { margin: 0 0 $spacing-2 0; }
    ul { padding-left: 20px; }
  }

  &__input-area {
    display: flex;
    gap: $spacing-2;
    padding: $spacing-3 $spacing-4;
    border-top: 1px solid $border-color-light;
    align-items: flex-end;
  }

  &__placeholder {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

.streaming {
  display: inline;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>
