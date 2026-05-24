<template>
  <div class="requirements-view">
    <!-- Header -->
    <div class="requirements-view__header">
      <div class="requirements-view__header-left">
        <h1>需求管理</h1>
        <div class="requirements-view__status" v-if="store.hermesStatus">
          <span
            class="requirements-view__status-dot"
            :class="store.hermesStatus.connected ? 'online' : 'offline'"
          />
          <span class="requirements-view__status-text">
            {{ store.hermesStatus.connected ? 'Hermes已连接' : 'Hermes就绪' }}
          </span>
          <el-tag size="small" type="info" v-if="store.hermesStatus.version">
            v{{ store.hermesStatus.version }}
          </el-tag>
        </div>
      </div>
      <div class="requirements-view__header-right">
        <el-button type="primary" @click="showCreateDialog = true">+ 创建项目</el-button>
        <el-button @click="handleRefresh">刷新</el-button>
      </div>
    </div>

    <el-alert v-if="store.error" :title="store.error" type="error" show-icon closable class="requirements-view__alert" />

    <!-- Project Selector -->
    <div class="requirements-view__toolbar">
      <el-select
        v-model="selectedProjectId"
        placeholder="选择或创建一个项目"
        size="large"
        style="width: 320px"
        @change="handleProjectChange"
      >
        <el-option v-for="p in store.projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>

      <el-steps :active="stepIndex" simple style="margin-left: 24px; flex: 1; max-width: 500px">
        <el-step title="讨论需求" :status="stepIndex > 0 ? 'success' : 'process'" />
        <el-step title="提交文档" :status="stepIndex > 1 ? 'success' : stepIndex === 1 ? 'process' : 'wait'" />
        <el-step title="确认锁定" :status="stepIndex > 2 ? 'success' : stepIndex === 2 ? 'process' : 'wait'" />
      </el-steps>
    </div>

    <!-- Main Body -->
    <div class="requirements-view__body" v-if="store.currentProject">
      <!-- Left: Chat -->
      <div class="requirements-view__chat-panel">
        <div class="requirements-view__panel-header">
          <h3>
            <span class="requirements-view__hermes-icon">🤖</span>
            Hermes 需求讨论
          </h3>
          <div class="requirements-view__panel-actions">
            <span class="requirements-view__round-count" v-if="chatRound > 0">第 {{ chatRound }} 轮</span>
            <el-button v-if="store.chatMessages.length > 0" text size="small" @click="handleClearChat">重新开始</el-button>
          </div>
        </div>

        <div class="requirements-view__chat" ref="chatRef">
          <div v-if="store.chatMessages.length === 0" class="requirements-view__chat-empty">
            <div class="requirements-view__chat-welcome">
              <div class="requirements-view__chat-avatar">🤖</div>
              <p>欢迎来到需求管理中心！</p>
              <p class="requirements-view__chat-sub">与 Hermes 对话，让 AI 帮你梳理、分析、完善项目需求。</p>
            </div>
            <div class="requirements-view__chat-starters">
              <el-button
                v-for="s in starters"
                :key="s"
                @click="handleStarterClick(s)"
                :disabled="store.chatLoading"
                class="requirements-view__starter-btn"
              >
                {{ s }}
              </el-button>
            </div>
          </div>

          <div
            v-for="(msg, idx) in store.chatMessages"
            :key="idx"
            :class="['requirements-view__chat-msg', msg.role]"
          >
            <div class="requirements-view__chat-avatar-small">
              {{ msg.role === 'hermes' ? '🤖' : '👤' }}
            </div>
            <div class="requirements-view__chat-bubble">{{ msg.content }}</div>
          </div>

          <div v-if="store.chatLoading" class="requirements-view__chat-msg hermes">
            <div class="requirements-view__chat-avatar-small">🤖</div>
            <div class="requirements-view__chat-bubble hermes-thinking">
              <span class="dot-pulse">思考中<span>.</span><span>.</span><span>.</span></span>
            </div>
          </div>

          <div v-if="chatQuestions.length > 0 && !store.chatLoading" class="requirements-view__chat-questions">
            <el-tag
              v-for="q in chatQuestions"
              :key="q"
              :class="['clickable', q === '提交需求并生成文档' ? 'el-tag--success' : '']"
              :type="q === '提交需求并生成文档' ? 'success' : 'primary'"
              effect="plain"
              @click="handleQuestionClick(q)"
            >
              {{ q.length > 30 ? q.slice(0, 30) + '...' : q }}
            </el-tag>
          </div>
        </div>

        <div class="requirements-view__chat-input">
          <el-input
            v-model="chatInput"
            type="textarea"
            :rows="2"
            :placeholder="chatPlaceholder"
            :disabled="store.chatLoading"
            @keyup.enter.ctrl="handleChatSend"
          />
          <el-button
            type="primary"
            size="large"
            :loading="store.chatLoading"
            :disabled="!chatInput.trim()"
            @click="handleChatSend"
            class="requirements-view__chat-send-btn"
          >
            <el-icon><Promotion /></el-icon>
            发送
          </el-button>
        </div>
      </div>

      <!-- Right: Requirement Document -->
      <div class="requirements-view__doc-panel">
        <div class="requirements-view__panel-header">
          <h3>
            <span class="requirements-view__doc-icon">📋</span>
            需求文档
          </h3>
          <div class="requirements-view__panel-actions">
            <el-tag v-if="store.isConfirmed" type="success" size="small" effect="dark">已确认</el-tag>
            <el-tag v-else-if="store.hasRequirement" type="warning" size="small">待确认</el-tag>
            <el-tag v-else type="info" size="small">草稿</el-tag>
          </div>
        </div>

        <div class="requirements-view__doc-editor">
          <el-input
            v-model="store.draftContent"
            type="textarea"
            :rows="12"
            :placeholder="docPlaceholder"
            :disabled="store.isConfirmed"
            @input="handleDraftChange"
          />
        </div>

        <div v-if="store.hasRequirement && !store.isConfirmed" class="requirements-view__doc-info">
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="当前版本">v{{ store.requirement?.version }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag size="small" type="warning">待确认</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="更新时间">
              {{ formatTime(store.requirement?.updated_at) }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="requirements-view__doc-actions">
          <el-button
            type="primary"
            size="large"
            :loading="store.submitting"
            :disabled="!store.draftContent.trim() || store.isConfirmed"
            @click="handleSubmit"
            class="requirements-view__action-btn"
          >
            提交需求文档
          </el-button>
          <el-tooltip content="讨论充分后，点击确认锁定需求，不可再修改" placement="top">
            <el-button
              type="success"
              size="large"
              :loading="store.loading"
              :disabled="!store.hasRequirement || store.isConfirmed"
              @click="handleConfirm"
              class="requirements-view__action-btn"
            >
              确认锁定 ✅
            </el-button>
          </el-tooltip>
          <el-tooltip content="锁定后将自动拆解为可执行任务" placement="top">
            <el-button
              size="large"
              :disabled="!store.isConfirmed"
              @click="handleDecompose"
            >
              拆解任务 ▶
            </el-button>
          </el-tooltip>
        </div>

        <div v-if="store.chatPhase === 'summarizing' && !store.hasRequirement" class="requirements-view__tip">
          <el-alert
            title="需求分析完成！点击「提交需求文档」保存讨论结果"
            type="success"
            show-icon
            :closable="false"
          />
        </div>
      </div>
    </div>

    <!-- No project selected -->
    <div v-else class="requirements-view__empty-state">
      <el-empty description="请选择或创建一个项目开始需求管理">
        <template #image>
          <div class="requirements-view__empty-icon">📋</div>
        </template>
        <el-button type="primary" @click="showCreateDialog = true">+ 创建项目</el-button>
      </el-empty>
    </div>

    <!-- Create Project Dialog -->
    <el-dialog v-model="showCreateDialog" title="创建项目" width="480px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="项目名称" required>
          <el-input v-model="createForm.name" placeholder="输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="简要描述项目目的（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="store.loading" :disabled="!createForm.name.trim()" @click="handleCreateProject">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRequirementStore } from '@/stores/useRequirementStore'
import { apiClient } from '@/api/client'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Promotion } from '@element-plus/icons-vue'

const store = useRequirementStore()

const selectedProjectId = ref('')
const chatInput = ref('')
const chatQuestions = ref<string[]>([])
const chatRound = ref(0)
const hermesSessionId = ref('')
const chatRef = ref<HTMLElement | null>(null)
const showCreateDialog = ref(false)
const createForm = ref({ name: '', description: '' })

const starters = [
  '我想开发一个电商平台',
  '我需要一个企业管理系统',
  '我想做一个移动App',
  '帮我分析我的项目需求',
]

const stepIndex = computed(() => {
  if (store.isConfirmed) return 3
  if (store.hasRequirement) return 2
  if (store.chatMessages.length > 2) return 1
  return 0
})

const chatPlaceholder = computed(() => {
  if (store.chatPhase === 'initial') return '描述你的项目想法，例如：我想做一个电商平台...'
  if (store.chatPhase === 'summarizing') return '需求已清晰！可以补充细节或点击提交...'
  return '回复 Hermes 的问题，完善需求分析...'
})

const docPlaceholder = computed(() => {
  if (!store.currentProject) return '请先选择项目'
  if (store.isConfirmed) return '需求已锁定，不可编辑'
  return '在此编辑需求文档，或通过左侧聊天自动生成...'
})

onMounted(async () => {
  await Promise.all([
    store.fetchProjects(),
    store.fetchHermesStatus(),
  ])
  if (store.projects.length > 0) {
    selectedProjectId.value = store.projects[0].id
    store.selectProject(selectedProjectId.value)
    // Auto-send intro
    setTimeout(() => handleStartChat(), 300)
  }
})

function formatTime(t?: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

async function handleStartChat() {
  const data = await store.sendIntro()
  if (data?.questions) {
    chatQuestions.value = data.questions
  }
}

async function handleProjectChange(val: string) {
  store.selectProject(val)
  chatQuestions.value = []
  chatRound.value = 0
  if (val) {
    setTimeout(() => handleStartChat(), 300)
  }
}

async function handleRefresh() {
  await Promise.all([
    store.fetchProjects(),
    store.fetchHermesStatus(),
  ])
  if (store.currentProjectId) {
    await store.fetchRequirement(store.currentProjectId)
  }
}

async function handleCreateProject() {
  const name = createForm.value.name.trim()
  if (!name) return
  const project = await store.createProject(name, createForm.value.description.trim() || undefined)
  if (project) {
    ElMessage.success(`项目「${project.name}」创建成功`)
    showCreateDialog.value = false
    createForm.value = { name: '', description: '' }
    selectedProjectId.value = project.id
    store.selectProject(project.id)
    setTimeout(() => handleStartChat(), 300)
  } else {
    // API 调用失败或响应结构不符：给出明确提示
    ElMessage.error(store.error || '创建项目失败，请重试')
  }
}

async function handleChatSend() {
  const text = chatInput.value.trim()
  if (!text || store.chatLoading.value) return
  chatInput.value = ''
  chatRound.value++
  store.chatMessages.push({ role: 'user', content: text })
  store.chatLoading.value = true

  const hermesMsg = { role: 'hermes', content: '' }
  store.chatMessages.push(hermesMsg)
  scrollToBottom()

  try {
    const token = localStorage.getItem('token') || ''
    const resp = await fetch('/api/hermes/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ message: text, session_id: hermesSessionId.value || undefined }),
    })

    if (!resp.ok || !resp.body) {
      throw new Error(`HTTP ${resp.status}`)
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      let currentEvent = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          const dataStr = line.slice(6)
          try {
            const data = JSON.parse(dataStr)
            if (currentEvent === 'content' && data.content) {
              hermesMsg.content += data.content
              scrollToBottom()
            } else if (currentEvent === 'done') {
              hermesMsg.content = data.content || hermesMsg.content
              if (data.tool_calls && data.tool_calls.length > 0) {
                hermesMsg.content += '\n\n🔧 工具调用: ' + data.tool_calls.map((tc: any) => tc.function?.name || 'tool').join(', ')
              }
              if (data.session_id) {
                hermesSessionId.value = data.session_id
              }
            } else if (currentEvent === 'error') {
              hermesMsg.content = data.message || '对话出错'
            } else if (currentEvent === 'session' && data.session_id) {
              hermesSessionId.value = data.session_id
            }
          } catch {}
        }
      }
    }
  } catch (e: any) {
    if (!hermesMsg.content) {
      hermesMsg.content = '暂时无法连接 Hermes Agent，请稍后重试。'
    }
  } finally {
    store.chatLoading.value = false
    scrollToBottom()
  }

  const questions: string[] = []
  for (const line of hermesMsg.content.split('\n')) {
    const s = line.trim()
    if (s && /[？?是否还是哪种多少什么明确确认]/.test(s) && s.length > 5 && s.length < 80) {
      questions.push(s.replace(/^[-*•]\s*/, '').replace(/^\d+\.\s*/, ''))
    }
  }
  chatQuestions.value = questions.slice(0, 5)

  if (hermesMsg.content && store.draftContent) {
    store.draftContent += '\n\n' + hermesMsg.content
  } else if (hermesMsg.content) {
    store.draftContent = hermesMsg.content
  }
}

function handleQuestionClick(q: string) {
  if (q === '提交需求并生成文档') {
    // 如果草稿有内容，自动提交
    if (store.draftContent.trim()) {
      handleSubmit()
    } else {
      // 用对话内容作为需求提交
      const chatContent = store.chatMessages
        .filter(m => m.role === 'user')
        .map(m => m.content)
        .join('\n')
      if (chatContent) {
        store.draftContent = chatContent
        handleSubmit()
      }
    }
    return
  }
  chatInput.value = q
  handleChatSend()
}

function handleStarterClick(s: string) {
  chatInput.value = s
  handleChatSend()
}

function handleDraftChange() {
  // 手动编辑草稿
}

async function handleSubmit() {
  if (!store.draftContent.trim()) {
    ElMessage.warning('请先描述需求内容')
    return
  }
  const ok = await store.submitRequirement(store.draftContent)
  if (ok) {
    ElMessage.success('需求文档已提交')
  }
}

async function handleConfirm() {
  try {
    await ElMessageBox.confirm(
      '确认锁定后需求文档将不可再修改，并将自动进入任务拆解流程。确定要锁定吗？',
      '确认需求',
      { confirmButtonText: '确认锁定', cancelButtonText: '取消', type: 'warning' },
    )
    const ok = await store.confirmRequirement()
    if (ok) {
      ElMessage.success('需求已确认锁定！')
      // 自动拆解
      setTimeout(() => handleDecompose(), 500)
    }
  } catch {
    // cancelled
  }
}

async function handleDecompose() {
  if (!store.currentProjectId) return
  try {
    const res = await apiClient.post(`/projects/${store.currentProjectId}/decompose`) as any
    const data = res?.data
    if (data?.total && data.total > 0) {
      ElMessage.success(`成功拆解 ${data.total} 个任务，可在看板中查看`)
    } else {
      ElMessage.info('拆解完成，请到看板查看任务')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '任务拆解失败')
  }
}

function handleClearChat() {
  store.chatMessages.splice(0, store.chatMessages.length)
  chatQuestions.value = []
  chatRound.value = 0
  setTimeout(() => handleStartChat(), 200)
}

function scrollToBottom() {
  setTimeout(() => {
    if (chatRef.value) {
      chatRef.value.scrollTop = chatRef.value.scrollHeight
    }
  }, 100)
}

watch(() => store.chatMessages.length, () => scrollToBottom())
</script>

<style scoped lang="scss">
.requirements-view {
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    &-left {
      display: flex;
      align-items: center;
      gap: 16px;
      h1 { margin: 0; font-size: 24px; font-weight: 600; }
    }
    &-right { display: flex; gap: 8px; }
  }

  &__status {
    display: flex; align-items: center; gap: 6px;
    &-dot {
      width: 10px; height: 10px; border-radius: 50%;
      &.online { background: #67c23a; box-shadow: 0 0 6px rgba(103,194,58,0.6); }
      &.offline { background: #e6a23c; }
    }
    &-text { font-size: 13px; color: #909399; }
  }

  &__alert { margin-bottom: 12px; }

  &__toolbar {
    display: flex;
    align-items: center;
    margin-bottom: 16px;
    padding: 12px 16px;
    background: #f5f7fa;
    border-radius: 8px;
  }

  &__body {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    min-height: 0;
  }

  // ── Chat Panel (Left) ──────────────────────────
  &__chat-panel {
    display: flex;
    flex-direction: column;
    background: #fff;
    border-radius: 8px;
    border: 1px solid #e4e7ed;
    overflow: hidden;
  }

  &__panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid #e4e7ed;
    h3 {
      margin: 0;
      font-size: 15px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
  }

  &__panel-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__round-count {
    font-size: 12px;
    color: #909399;
    background: #f0f2f5;
    padding: 2px 8px;
    border-radius: 10px;
  }

  &__chat {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    background: #fafafa;

    &-empty {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
    }

    &-welcome {
      text-align: center;
      p { margin: 4px 0; font-size: 15px; }
    }

    &-sub { color: #909399; font-size: 13px !important; }

    &-avatar { font-size: 48px; }

    &-starters {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: center;
    }

    &-avatar-small {
      font-size: 24px;
      flex-shrink: 0;
    }

    &-msg {
      display: flex;
      gap: 8px;
      align-items: flex-start;

      &.user {
        flex-direction: row-reverse;
        .requirements-view__chat-bubble {
          background: #409eff;
          color: #fff;
          border-bottom-right-radius: 4px;
        }
      }

      &.hermes {
        .requirements-view__chat-bubble {
          background: #fff;
          color: #303133;
          border: 1px solid #e4e7ed;
          border-bottom-left-radius: 4px;
        }
      }
    }

    &-bubble {
      max-width: 80%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 14px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-word;

      &.hermes-thinking {
        color: #909399;
      }
    }

    &-questions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 4px 16px 0;
      .clickable { cursor: pointer; transition: opacity 0.2s; &:hover { opacity: 0.8; } }
    }
  }

  &__chat-input {
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    border-top: 1px solid #e4e7ed;
    align-items: flex-end;
    background: #fff;
  }

  &__chat-send-btn {
    flex-shrink: 0;
    height: 56px;
  }

  // ── Document Panel (Right) ─────────────────────
  &__doc-panel {
    display: flex;
    flex-direction: column;
    background: #fff;
    border-radius: 8px;
    border: 1px solid #e4e7ed;
    overflow: hidden;
  }

  &__doc-icon { font-size: 18px; }

  &__doc-editor {
    padding: 16px;
    flex: 1;
    :deep(textarea) {
      font-family: inherit;
      line-height: 1.6;
    }
  }

  &__doc-info {
    padding: 0 16px 12px;
  }

  &__doc-actions {
    padding: 12px 16px;
    border-top: 1px solid #e4e7ed;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  &__action-btn {
    flex: 1;
    min-width: 120px;
  }

  &__tip {
    padding: 12px 16px;
  }

  // ── Empty State ──────────────────────────────
  &__empty-state {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  &__empty-icon { font-size: 64px; }
}

// Dot pulse animation
.dot-pulse span {
  animation: dot-pulse 1.4s infinite;
  opacity: 0;
  &:nth-child(1) { animation-delay: 0s; }
  &:nth-child(2) { animation-delay: 0.2s; }
  &:nth-child(3) { animation-delay: 0.4s; }
}
@keyframes dot-pulse {
  0%, 60%, 100% { opacity: 0; }
  30% { opacity: 1; }
}
</style>
