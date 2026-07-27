<template>
  <div class="step3-view" v-loading="store.loading">
    <div class="step3-view__header">
      <div class="step3-view__header-left">
        <el-button :icon="ArrowLeft" text @click="goBack">返回</el-button>
        <div>
          <h1>第三步：需求分析</h1>
          <p class="step3-view__subtitle">{{ projectName }} · 后兴（HouXing）需求分析师</p>
        </div>
      </div>
      <div class="step3-view__header-right">
        <el-tag :type="phaseTagType" effect="dark" size="large">{{ phaseLabel }}</el-tag>
      </div>
    </div>

    <div class="step3-view__progress">
      <div
        v-for="(p, i) in phases"
        :key="p.key"
        class="step3-view__progress-step"
        :class="{
          'step3-view__progress-step--active': p.key === currentPhase,
          'step3-view__progress-step--done': phaseIndex > i,
        }"
      >
        <div class="step3-view__progress-indicator">
          <span v-if="phaseIndex > i">✓</span>
          <span v-else>{{ i + 1 }}</span>
        </div>
        <div class="step3-view__progress-label">{{ p.label }}</div>
      </div>
    </div>

    <el-alert v-if="store.error" :title="store.error" type="error" show-icon closable class="step3-view__alert" />

    <div v-if="currentPhase === 'discuss'" class="step3-view__chat-section">
      <div class="step3-view__chat-panel">
        <div class="step3-view__panel-header">
          <h3>
            <span class="step3-view__houxing-icon">📋</span>
            后兴（HouXing）· 需求分析师
          </h3>
          <div class="step3-view__panel-actions">
            <span class="step3-view__round-count" v-if="chatMessages.length > 0">已发送 {{ chatRound }} 条消息</span>
          </div>
        </div>

        <div class="step3-view__chat" ref="chatRef">
          <div v-if="chatMessages.length === 0 && !chatLoading" class="step3-view__chat-empty">
            <div class="step3-view__empty-icon">📋</div>
            <p>后兴正在准备，请稍候...</p>
          </div>

          <div
            v-for="(msg, idx) in chatMessages"
            :key="idx"
            :class="['step3-view__chat-msg', msg.role]"
          >
            <div class="step3-view__chat-avatar">
              {{ msg.role === 'houxing' ? '📋' : msg.role === 'system' ? '⚙️' : '👤' }}
            </div>
            <div class="step3-view__chat-bubble">
              <div class="step3-view__chat-time">
                <span v-if="msg.started_at">{{ msg.started_at }}</span>
                <span v-if="msg.started_at && msg.ended_at && msg.started_at !== msg.ended_at"> ~ {{ msg.ended_at }}</span>
              </div>
              <div v-html="renderContent(msg.content)"></div>
            </div>
          </div>

          <div v-if="chatLoading" class="step3-view__chat-msg houxing">
            <div class="step3-view__chat-avatar">📋</div>
            <div class="step3-view__chat-bubble step3-view__chat-thinking">
              <span class="dot-pulse">后兴正在分析您的需求<span>.</span><span>.</span><span>.</span></span>
            </div>
          </div>
        </div>

      </div>

      <div class="step3-view__summary-panel">
        <div class="step3-view__panel-header">
          <h3>
            <span class="step3-view__summary-icon">📄</span>
            需求文档
          </h3>
          <el-tag v-if="docContent" type="success" size="small">已生成</el-tag>
          <el-tag v-else type="info" size="small">未生成</el-tag>
        </div>
        <div class="step3-view__summary-content">
          <div class="step3-view__docs-path">
            <el-input v-model="docsPath" :placeholder="projectFolder" size="small" clearable>
              <template #prepend>📂</template>
            </el-input>
          </div>
          <div v-if="extractedDocs.length > 0" class="step3-view__doc-list" style="margin-top: 8px;">
            <div
              v-for="doc in extractedDocs"
              :key="doc.id"
              class="step3-view__doc-list-item"
              :class="{ 'step3-view__doc-list-item--selected': doc.selected }"
              @click="toggleDocSelection(doc.id)"
            >
              <el-checkbox :model-value="doc.selected" @click.stop="toggleDocSelection(doc.id)" />
              <div class="step3-view__doc-list-item-name" @click.stop="previewDoc(doc)">{{ doc.name }}</div>
              <el-icon><View /></el-icon>
            </div>
          </div>
          <div v-else class="step3-view__doc-empty">
            <p>输入文档文件夹路径，与后兴讨论后文档将自动显示在此。</p>
          </div>
        </div>
        <div class="step3-view__summary-actions">
          <el-button
            v-if="chatRound >= 1 && currentPhase === 'discuss'"
            type="primary"
            size="large"
            @click="handleFinishDiscuss"
            :loading="chatLoading"
            class="step3-view__action-btn"
          >
            完成讨论，提交文档
          </el-button>
        </div>
      </div>
    </div>

    <Teleport to=".app-main">
      <div v-if="currentPhase === 'discuss'" class="step3-chat-input">
        <el-input
          v-model="chatInput"
          type="textarea"
          :rows="2"
          placeholder="描述您的需求细节..."
          :disabled="chatLoading"
          @keyup.enter.ctrl="handleSend"
        />
        <el-button
          type="primary"
          size="large"
          :loading="chatLoading"
          :disabled="!chatInput.trim() || chatLoading"
          @click="handleSend"
          class="step3-view__send-btn"
        >
          <el-icon><Promotion /></el-icon>
          发送
        </el-button>
      </div>
    </Teleport>

    <div v-if="currentPhase === 'submit'" class="step3-view__submit-section">
      <div class="step3-view__submit-card">
        <div class="step3-view__submit-header">
          <div class="step3-view__submit-icon">📄</div>
          <h2>提交需求文档</h2>
        </div>
        <p class="step3-view__submit-subtitle">后兴生成的最新需求文档，确认后提交给后荣审查</p>

        <div class="step3-view__submit-preview">
          <div class="step3-view__doc-list">
            <div
              v-for="doc in extractedDocs"
              :key="doc.id"
              class="step3-view__doc-list-item"
              :class="{ 'step3-view__doc-list-item--selected': doc.selected }"
              @click="toggleDocSelection(doc.id)"
            >
              <el-checkbox :model-value="doc.selected" @click.stop="toggleDocSelection(doc.id)" />
              <div class="step3-view__doc-list-item-name" @click.stop="previewDoc(doc)">{{ doc.name }}</div>
              <el-icon><View /></el-icon>
            </div>
          </div>
        </div>

        <div class="step3-view__submit-actions">
          <el-button size="large" @click="backToDiscuss">返回修改</el-button>
          <el-button type="primary" size="large" :loading="submitting" @click="handleSubmitDocToQA">
            提交文档
          </el-button>
        </div>
      </div>
    </div>

    <el-dialog v-model="docPreviewVisible" title="需求文档预览" width="800px">
      <div class="step3-view__doc-preview-dialog">
        <pre>{{ docContent }}</pre>
      </div>
      <template #footer>
        <el-button @click="docPreviewVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <div v-if="currentPhase === 'qa'" class="step3-view__qa-section">
      <div class="step3-view__qa-card">
        <div class="step3-view__qa-header">
          <div class="step3-view__qa-icon">🔍</div>
          <h2>后荣（HouRong）· QA 检验</h2>
        </div>
        <p class="step3-view__qa-subtitle">检验需求文档是否达到验收标准</p>

        <div v-if="qaLoading" class="step3-view__qa-loading">
          <el-progress :percentage="qaProgress" :stroke-width="6" :status="qaProgress >= 100 ? 'success' : 'warning'" />
          <div class="step3-view__qa-stream">
            <p v-for="(line, i) in qaStreamLines" :key="i" class="step3-view__qa-stream-line">{{ line }}</p>
            <p v-if="qaStreamBuffer" class="step3-view__qa-stream-line step3-view__qa-stream-line--active">{{ qaStreamBuffer }}<span class="step3-view__qa-cursor">|</span></p>
          </div>
        </div>

        <div v-else-if="qaChecked" class="step3-view__qa-dimensions">

          <!-- TODO List 检验报告 -->
          <div class="step3-view__qa-todolist">
            <div class="step3-view__qa-todolist-header">
              <div class="step3-view__qa-todolist-title">
                <span class="step3-view__qa-todolist-icon">📋</span>
                <span>检验报告</span>
              </div>
              <el-tag :type="todoItems.every(t => t.status === 'passed') ? 'success' : 'warning'" size="small">
                {{ todoItems.filter(t => t.status === 'passed').length }}/{{ todoItems.length }} 完成
              </el-tag>
            </div>

            <div
              v-for="(item, idx) in todoItems"
              :key="item.key"
              class="step3-view__qa-todoitem"
              :class="{
                'step3-view__qa-todoitem--done': item.status === 'passed',
                'step3-view__qa-todoitem--fixing': item.status === 'fixing',
                'step3-view__qa-todoitem--verifying': item.status === 'verifying',
                'step3-view__qa-todoitem--failed': item.status === 'failed',
                'step3-view__qa-todoitem--pending': item.status === 'pending',
              }"
            >
              <div class="step3-view__qa-todoitem-checkbox">
                <el-checkbox :model-value="item.status === 'passed'" disabled />
              </div>
              <div class="step3-view__qa-todoitem-body">
                <div class="step3-view__qa-todoitem-label">{{ item.label }}</div>
                <div class="step3-view__qa-todoitem-detail">{{ item.detail }}</div>
              </div>
              <div class="step3-view__qa-todoitem-badge">
                <el-tag v-if="item.status === 'passed'" type="success" size="small" effect="dark">✅ 已修复</el-tag>
                <el-tag v-else-if="item.status === 'fixing'" type="warning" size="small" effect="dark">🔧 修复中</el-tag>
                <el-tag v-else-if="item.status === 'verifying'" type="warning" size="small" effect="dark">🔍 检验中</el-tag>
                <el-tag v-else-if="item.status === 'failed'" type="danger" size="small" effect="dark">❌ 未通过</el-tag>
                <el-tag v-else type="info" size="small" effect="dark">⏳ 待修复</el-tag>
              </div>
            </div>
          </div>

          <el-divider />

          <!-- 最终结果 -->
          <div class="step3-view__qa-result-area">
            <div v-if="qaPassed" class="step3-view__qa-result step3-view__qa-result--passed">
              <el-result icon="success" title="所有检验项目均通过 ✅" sub-title="需求文档已达到验收标准">
                <template #extra>
                  <el-button type="primary" @click="handleComplete">进入下一步 ➜</el-button>
                </template>
              </el-result>
            </div>
            <div v-else-if="qaChecked && !qaLoading" class="step3-view__qa-result step3-view__qa-result--failed">
              <el-result icon="error" title="部分检验项目未通过" sub-title="请手动修改后重新检验">
                <template #extra>
                  <el-button type="primary" @click="handleRunQA">重新检验</el-button>
                </template>
              </el-result>
            </div>
          </div>
        </div>

        <div v-else class="step3-view__qa-waiting">
          <p class="step3-view__qa-waiting-text">后荣将逐项检验以下维度：</p>
          <div class="step3-view__qa-dimension-list">
            <div v-for="dim in SRS_DIMENSIONS" :key="dim.key" class="step3-view__qa-dimension-item">
              <span class="step3-view__qa-dimension-item-label">{{ dim.label }}</span>
              <span class="step3-view__qa-dimension-item-desc">{{ dim.description }}</span>
            </div>
          </div>
          <el-button type="primary" size="large" @click="handleRunQA" :loading="qaLoading">
            开始 QA 检验
          </el-button>
        </div>
      </div>
    </div>

    <div v-if="currentPhase === 'complete'" class="step3-view__complete-section">
      <div class="step3-view__complete-card">
        <div class="step3-view__complete-icon">🎉</div>
        <h2>第三步完成！</h2>
        <p class="step3-view__complete-subtitle">需求分析已全部完成</p>

        <el-divider />

        <div class="step3-view__complete-summary">
          <div class="step3-view__complete-item">
            <div class="step3-view__complete-item-icon">📄</div>
            <div class="step3-view__complete-item-content">
              <div class="step3-view__complete-item-label">需求文档</div>
              <div class="step3-view__complete-item-value">已生成并确认</div>
            </div>
            <el-tag type="success" size="small" effect="dark">已完成</el-tag>
          </div>
        </div>

        <el-divider />

        <div class="step3-view__complete-actions">
          <el-button size="large" @click="goBack">返回项目</el-button>
          <el-button type="primary" size="large" @click="handleGoNext">
            进入下一步 ➜
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Promotion, View } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRequirementStore } from '@/stores/useRequirementStore'
import { workflowApi } from '@/api/modules/workflow'

interface ChatMessage {
  role: 'houxing' | 'user' | 'system'
  content: string
  started_at?: string
  ended_at?: string
}

function nowStr(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

const router = useRouter()
const route = useRoute()
const store = useRequirementStore()

const projectId = computed(() => route.params.projectId as string)
const projectName = computed(() => route.query.name as string || '未命名项目')

const chatInput = ref('')
const chatRef = ref<HTMLElement | null>(null)
const chatMessages = ref<ChatMessage[]>([])
const chatRound = ref(0)
const chatLoading = ref(false)
const currentPhase = ref<'discuss' | 'submit' | 'qa' | 'complete'>('discuss')
const docContent = ref('')
interface InspectionDimension {
  key: string
  label: string
  description: string
  passed: boolean
  detail: string
}

const SRS_DIMENSIONS = [
  { key: 'completeness', label: '完整性', description: '需求文档是否覆盖了所有必要的功能和非功能需求' },
  { key: 'consistency', label: '一致性', description: '文档内容前后是否一致，术语定义是否统一' },
  { key: 'verifiability', label: '可验证性', description: '每个需求是否可量化、可测试、可验证' },
  { key: 'unambiguity', label: '无歧义性', description: '需求描述是否清晰明确，不存在二义性理解' },
]

const submitting = ref(false)
const savedDocPath = ref('')
const qaLoading = ref(false)
const qaProgress = ref(0)
const qaPassed = ref(false)
const qaChecked = ref(false)
const qaAutoAdvance = ref(false)
const qaMessage = ref('')
const qaDimensions = ref<InspectionDimension[]>([])
interface TodoItem {
  key: string
  label: string
  detail: string
  status: 'pending' | 'fixing' | 'verifying' | 'passed' | 'failed'
}
const todoItems = ref<TodoItem[]>([])
const docPreviewVisible = ref(false)

// QA WebSocket 流式检验
let qaWs: WebSocket | null = null
const qaStreamText = ref('')
const qaStreamBuffer = ref('')

interface ExtractedDoc {
  id: number
  name: string
  content: string
  selected: boolean
}
const extractedDocs = ref<ExtractedDoc[]>([])
const docsPath = ref(route.query.docsPath as string || '')
const projectFolder = computed(() => {
  const p = store.projects.find(p => p.id === projectId.value)
  return p?.project_dir || ''
})

let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let pendingMessages: string[] = []
let introSent = false
let autosaveTimer: ReturnType<typeof setInterval> | null = null

const phases = [
  { key: 'discuss', label: '需求讨论' },
  { key: 'submit', label: '提交文档' },
  { key: 'qa', label: 'QA检验' },
  { key: 'complete', label: '完成' },
]

const phaseIndex = computed(() => {
  const idx = phases.findIndex(p => p.key === currentPhase.value)
  return idx >= 0 ? idx : 0
})

const phaseLabel = computed(() => {
  const p = phases.find(p => p.key === currentPhase.value)
  return p?.label || currentPhase.value
})

const phaseTagType = computed(() => {
  const map: Record<string, string> = {
    discuss: 'primary',
    submit: 'warning',
    qa: 'warning',
    complete: 'success',
  }
  return map[currentPhase.value] || 'info'
})



const qaStreamLines = computed(() =>
  qaStreamText.value.split('\n').filter(l => l.trim())
)

function getWsUrl(): string {
  const token = localStorage.getItem('access_token') || ''
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/step3/chat/${projectId.value}?token=${token}`
}

function flushPending() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return
  while (pendingMessages.length > 0) {
    const msg = pendingMessages.shift()!
    ws.send(msg)
  }
}

function connectWebSocket() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
  ws = new WebSocket(getWsUrl())

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)

    if (msg.type === 'chunk') {
      const last = chatMessages.value[chatMessages.value.length - 1]
      if (last && last.role === 'houxing' && last.content !== '') {
        last.content += msg.content
      } else {
        chatMessages.value.push({ role: 'houxing', content: msg.content, started_at: nowStr() })
      }
      scrollToBottom()
    }

    if (msg.type === 'done') {
      const last = chatMessages.value[chatMessages.value.length - 1]
      if (last && last.role === 'houxing') last.ended_at = nowStr()
      chatLoading.value = false
      scrollToBottom()
      saveHouXingResponse()
      saveChatSession()
    }

    if (msg.type === 'error') {
      const last = chatMessages.value[chatMessages.value.length - 1]
      if (last && last.role === 'houxing' && last.content === '') {
        chatMessages.value.pop()
      }
      const errTime = nowStr()
      chatMessages.value.push({
        role: 'houxing',
        content: '抱歉，与后兴通信失败，请稍后重试。',
        started_at: errTime,
        ended_at: errTime,
      })
      chatLoading.value = false
      scrollToBottom()
    }
  }

  ws.onopen = () => {
    flushPending()
    if (!introSent && chatMessages.value.length === 0) {
      introSent = true
      chatLoading.value = true
      pendingMessages.push(JSON.stringify({ message: '', history: [], doc_save_counter: docSaveCounter }))
      flushPending()
    } else {
      introSent = true
    }
  }

  ws.onclose = () => {
    ws = null
    if (chatLoading.value) {
      reconnectTimer = setTimeout(connectWebSocket, 3000)
    }
  }

  ws.onerror = () => {
    ws?.close()
  }
}

function sendWsMessage(message: string) {
  const history = chatMessages.value.map(m => ({
    role: m.role === 'houxing' ? 'assistant' : m.role,
    content: m.content,
  }))
  const payload = JSON.stringify({ message, history, doc_save_counter: docSaveCounter })
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    pendingMessages.push(payload)
    connectWebSocket()
    return
  }
  ws.send(payload)
}

function getQaWsUrl(): string {
  const token = localStorage.getItem('access_token') || ''
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/step3/qa/${projectId.value}?token=${token}`
}

async function saveChatSession() {
  if (!projectId.value) return
  try {
    await workflowApi.saveStep3Artifacts(projectId.value, {
      chat_messages: chatMessages.value.map(m => ({ role: m.role, content: m.content })),
      chat_round: chatRound.value,
      doc_content: docContent.value,
      current_phase: currentPhase.value,
      saved_doc_path: savedDocPath.value,
      qa_dimensions: qaDimensions.value,
      qa_passed: qaPassed.value,
      qa_checked: qaChecked.value,
      qa_message: qaMessage.value,
      todo_items: todoItems.value,
      extracted_docs: extractedDocs.value.map(d => ({ id: d.id, name: d.name, content: d.content, selected: d.selected })),
      doc_save_counter: docSaveCounter,
    })
  } catch {
    // 静默保存失败
  }
}

async function restoreChatSession() {
  try {
    const res = await workflowApi.getStep3Status(projectId.value) as any
    const data = res?.data || res
    if (data?.chat_messages?.length > 0) {
      chatMessages.value = data.chat_messages.map((m: any) => ({ role: m.role, content: m.content, started_at: m.started_at, ended_at: m.ended_at }))
      chatRound.value = data.chat_round || 0
      if (data.doc_content) {
        docContent.value = data.doc_content
      }
      if (data.current_phase && ['discuss', 'submit', 'qa', 'complete'].includes(data.current_phase)) {
        currentPhase.value = data.current_phase
      }
      if (data.saved_doc_path) {
        savedDocPath.value = data.saved_doc_path
      }
      if (data.qa_dimensions) {
        qaDimensions.value = data.qa_dimensions
      }
      if (typeof data.qa_passed === 'boolean') {
        qaPassed.value = data.qa_passed
      }
      if (typeof data.qa_checked === 'boolean') {
        qaChecked.value = data.qa_checked
      }
      if (data.qa_message) {
        qaMessage.value = data.qa_message
      }
      if (data.todo_items) {
        todoItems.value = data.todo_items
      }
      if (data.extracted_docs) {
        extractedDocs.value = data.extracted_docs
      }
      if (typeof data.doc_save_counter === 'number') {
        docSaveCounter = data.doc_save_counter
      }
      introSent = true
    }
  } catch {
    // 静默恢复失败
  }
}

function handleBeforeUnload() {
  if (!projectId.value) return
  const payload = {
    chat_messages: chatMessages.value.map(m => ({ role: m.role, content: m.content })),
    chat_round: chatRound.value,
    doc_content: docContent.value,
    current_phase: currentPhase.value,
    saved_doc_path: savedDocPath.value,
    qa_dimensions: qaDimensions.value,
    qa_passed: qaPassed.value,
    qa_checked: qaChecked.value,
    qa_message: qaMessage.value,
    todo_items: todoItems.value,
    extracted_docs: extractedDocs.value.map(d => ({ id: d.id, name: d.name, content: d.content, selected: d.selected })),
    doc_save_counter: docSaveCounter,
  }
  navigator.sendBeacon(`/api/v1/workflow/${projectId.value}/step3/artifacts`, JSON.stringify(payload))
}

onMounted(async () => {
  if (!projectId.value) {
    ElMessage.error('缺少项目ID')
    router.push({ name: 'ProjectList' })
    return
  }
  await store.fetchProjects()
  store.selectProject(projectId.value)
  if (store.draftContent) {
    docContent.value = store.draftContent
  }

  const project = store.projects.find(p => p.id === projectId.value)
  if (!docsPath.value && project?.project_dir) {
    docsPath.value = project.project_dir + '/docs'
  }

  await restoreChatSession()
  connectWebSocket()

  if (docsPath.value) await loadDocsList()
  autosaveTimer = setInterval(() => saveChatSession(), 30000)
  window.addEventListener('beforeunload', handleBeforeUnload)
})

watch(docsPath, () => {
  if (docsPath.value) loadDocsList()
})

onUnmounted(() => {
  saveChatSession()
  if (autosaveTimer) clearInterval(autosaveTimer)
  window.removeEventListener('beforeunload', handleBeforeUnload)
  if (ws) {
    ws.onclose = null
    ws.close()
    ws = null
  }
  if (qaWs) {
    qaWs.onclose = null
    qaWs.close()
    qaWs = null
  }
})

let docSaveCounter = 0

async function loadDocsList() {
  if (!docsPath.value) return
  try {
    const res = await workflowApi.listStep3Docs(projectId.value, docsPath.value) as any
    const data = res?.data || res
    const files: { name: string; path: string; content: string }[] = data?.files || []
    const currentSelected = extractedDocs.value.find(d => d.selected)
    extractedDocs.value = files.map((f, i) => ({
      id: i + 1,
      name: f.name,
      content: f.content,
      selected: currentSelected?.name === f.name || (i === 0 && !currentSelected),
    }))
    const selected = extractedDocs.value.find(d => d.selected)
    if (selected) docContent.value = selected.content
  } catch (e) {
    console.warn('读取文档列表失败:', e)
  }
}

async function saveHouXingResponse() {
  // 文档由 houxing agent 后台生成并写入磁盘，不从聊天内容提取
  if (docsPath.value) await loadDocsList()
}

function toggleDocSelection(docId: number) {
  for (const doc of extractedDocs.value) {
    doc.selected = doc.id === docId
  }
  const selected = extractedDocs.value.find(d => d.selected)
  if (selected) docContent.value = selected.content
}

function previewDoc(doc: ExtractedDoc) {
  docContent.value = doc.content
  docPreviewVisible.value = true
}

function handleSend() {
  const text = chatInput.value.trim()
  if (!text || chatLoading.value) return
  chatInput.value = ''
  chatMessages.value.push({ role: 'user', content: text, started_at: nowStr(), ended_at: nowStr() })
  chatRound.value++
  chatLoading.value = true
  sendWsMessage(text)
}

async function handleFinishDiscuss() {
  await saveChatSession()

  const selected = extractedDocs.value.find(d => d.selected)
  if (!selected) {
    ElMessage.warning('请先与后兴讨论生成需求文档，然后在右侧面板勾选要提交的文档')
    return
  }
  docContent.value = selected.content

  await doSaveAndSubmit()
}

async function doSaveAndSubmit() {
  if (!docContent.value?.trim()) {
    ElMessage.warning('需求文档内容为空，请先与后兴讨论生成文档')
    return
  }
  submitting.value = true
  try {
    const selected = extractedDocs.value.find(d => d.selected)
    const filename = selected?.name || undefined
    const saveRes = await workflowApi.saveStep3Doc(projectId.value, docContent.value, filename) as any
    const saveData = saveRes?.data || saveRes
    if (saveRes?.code === 0 || saveData?.filepath) {
      savedDocPath.value = saveData?.filepath || 'docs/requirements.md'
      ElMessage.success(`需求文档已保存到代码库: ${savedDocPath.value}`)
    } else {
      ElMessage.warning(saveRes?.message || '保存到代码库失败')
    }
    await doSubmit()
  } catch (e: any) {
    ElMessage.warning('保存到代码库失败')
    await doSubmit()
  } finally {
    submitting.value = false
  }
}

async function doSubmit() {
  if (!docContent.value?.trim()) return
  submitting.value = true
  try {
    const ok = await store.submitRequirement(docContent.value)
    if (ok) {
      ElMessage.success('需求文档已提交')
      currentPhase.value = 'qa'
      await saveChatSession()
    }
  } finally {
    submitting.value = false
  }
}

async function handleSubmitDoc() {
  if (!docContent.value.trim()) {
    ElMessage.warning('需求文档内容不能为空，请先编写或从讨论中生成文档内容')
    return
  }
  submitting.value = true
  try {
    // 先保存到代码库
    if (docContent.value.trim()) {
      try {
        const saveRes = await workflowApi.saveStep3Doc(projectId.value, docContent.value) as any
        const saveData = saveRes?.data || saveRes
        if (saveRes?.code === 0 || saveData?.filepath) {
          savedDocPath.value = saveData?.filepath || 'docs/requirements.md'
          ElMessage.success(`需求文档已保存到代码库: ${savedDocPath.value}`)
        } else {
          ElMessage.warning(saveRes?.message || '保存到代码库失败')
        }
      } catch (e: any) {
        ElMessage.warning('保存到代码库失败')
      }
    }

    const ok = await store.submitRequirement(docContent.value)
    if (ok) {
      ElMessage.success('需求文档已提交')
      currentPhase.value = 'qa'
    }
  } finally {
    submitting.value = false
  }
}

async function handleRunQA() {
  const content = docContent.value || store.requirement?.content || ''
  if (!content.trim()) {
    ElMessage.warning('需求文档内容为空')
    return
  }

  qaLoading.value = true
  qaChecked.value = false
  qaProgress.value = 0
  qaStreamText.value = ''
  qaStreamBuffer.value = ''

  if (qaWs) { qaWs.onclose = null; qaWs.close(); qaWs = null }

  try {
    qaWs = new WebSocket(getQaWsUrl())

    await new Promise<void>((resolve, reject) => {
      let done = false

      qaWs!.onmessage = (event) => {
        const msg = JSON.parse(event.data)

        if (msg.type === 'progress') {
          qaStreamBuffer.value += msg.content
          qaProgress.value = Math.min(qaProgress.value + 2, 85)
        }

        if (msg.type === 'result') {
          const dims: InspectionDimension[] = msg.dimensions || []
          qaDimensions.value = dims
          qaPassed.value = msg.all_passed ?? dims.every(d => d.passed)
          qaMessage.value = qaPassed.value ? '所有检验项目均通过 ✅' : '部分检验项目未通过'
          qaChecked.value = true

          const failedDims = dims.filter(d => !d.passed)
          todoItems.value = failedDims.map(d => ({
            key: d.key, label: d.label, detail: d.detail,
            status: (msg.all_passed ? 'passed' : 'pending') as 'passed' | 'pending',
          }))

          if (!msg.all_passed) {
            qaProgress.value = 75
          }
        }

        if (msg.type === 'error') {
          qaStreamText.value += `\n❌ 错误: ${msg.message}`
          if (!done) { done = true; reject(new Error(msg.message)) }
        }

        if (msg.type === 'step_complete') {
          qaPassed.value = true
          qaChecked.value = true
          qaAutoAdvance.value = true
          if (!done) { done = true; resolve() }
        }
      }

      // WS 关闭 —— 有 result 即视为正常完成（pass/fail 均由 result 反映）
      qaWs!.onclose = () => {
        if (!done) {
          done = true
          if (qaChecked.value) resolve()
          else reject(new Error('QA WebSocket 连接关闭'))
        }
      }

      qaWs!.onerror = () => {
        if (!done) { done = true; reject(new Error('QA WebSocket 连接失败')) }
      }

      qaWs!.onopen = () => {
        qaWs!.send(JSON.stringify({
          action: 'inspect',
          content,
          docs_path: docsPath.value || undefined,
        }))
      }
    })

    await saveChatSession()
    if (qaPassed.value && qaAutoAdvance.value) {
      ElMessage.success('所有检验项目均通过！即将进入第4步...')
      await handleComplete()
    } else if (qaPassed.value) {
      ElMessage.success('QA 检验通过！')
    } else {
      ElMessage.warning('部分项目未能修复')
    }
  } catch (e: any) {
    if (!qaPassed.value) {
      ElMessage.error('QA 检验失败: ' + (e.message || '未知错误'))
    }
  } finally {
    qaLoading.value = false
    qaProgress.value = 100
  }
}

async function handleSubmitDocToQA() {
  if (!docContent.value?.trim()) {
    ElMessage.warning('需求文档内容为空')
    return
  }
  await doSaveAndSubmit()
  if (currentPhase.value === 'qa') {
    await handleRunQA()
  }
}

function backToDiscuss() {
  currentPhase.value = 'discuss'
  qaChecked.value = false
  qaPassed.value = false
  qaMessage.value = ''
  qaDimensions.value = []
  todoItems.value = []
}

async function handleComplete() {
  currentPhase.value = 'complete'
  await saveChatSession()
  ElMessage.success('第三步完成！')
  setTimeout(() => {
    router.push({ name: 'ProjectDetail', params: { projectId: projectId.value } })
  }, 1500)
}

function handleGoNext() {
  router.push({ name: 'ProjectDetail', params: { projectId: projectId.value } })
}

function goBack() {
  router.push({ name: 'ProjectDetail', params: { projectId: projectId.value } })
}

function renderContent(text: string) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function scrollToBottom() {
  nextTick(() => {
    if (chatRef.value) {
      chatRef.value.scrollTop = chatRef.value.scrollHeight
    }
  })
}
</script>

<style scoped lang="scss">
.step3-view {
  height: 98%;
  min-height: 0;
  display: flex;
  flex-direction: column;

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: $spacing-sm;
    &-left { display: flex; align-items: flex-start; gap: $spacing-sm;
      h1 { margin: 0; font-family: $font-display; font-size: $display-md-size; font-weight: $display-lg-weight; line-height: $display-lg-leading; color: $ink; }
    }
    &-right { flex-shrink: 0; }
  }
  &__subtitle { margin: $spacing-xxs 0 0; font-size: $caption-size; color: $ink-muted-48; }
  &__alert { margin-bottom: $spacing-sm; }

  &__progress {
    display: flex; align-items: center; gap: 0; margin-bottom: $spacing-4;
    padding: $spacing-sm $spacing-4; background: $canvas; border: 1px solid $hairline; border-radius: $radius-lg; overflow-x: auto;
    &-step {
      display: flex; align-items: center; gap: $spacing-xs; padding: 0 $spacing-sm; position: relative; flex-shrink: 0;
      &::after { content: ''; position: absolute; right: -$spacing-xs; top: 50%; width: 8px; height: 8px; border-right: 2px solid $hairline; border-bottom: 2px solid $hairline; transform: translateY(-50%) rotate(-45deg); }
      &:last-child::after { display: none; }
      &--done {
        .step3-view__progress-indicator { background: $status-done; color: $on-primary; border-color: $status-done; }
        .step3-view__progress-label { color: $status-done; }
      }
      &--active {
        .step3-view__progress-indicator { background: $primary; color: $on-primary; border-color: $primary; }
        .step3-view__progress-label { color: $primary; font-weight: 600; }
      }
    }
    &-indicator { width: 24px; height: 24px; border-radius: 50%; border: 2px solid $hairline; display: flex; align-items: center; justify-content: center; font-size: $fine-print-size; font-weight: 600; color: $ink-muted-48; flex-shrink: 0; }
    &-label { font-size: $caption-size; color: $ink-muted-48; white-space: nowrap; }
  }

  &__chat-section { flex: 1; display: grid; grid-template-columns: 1fr 380px; gap: $spacing-4; min-height: 0; }
  &__chat-panel { display: flex; flex-direction: column; background: $canvas; border-radius: $radius-lg; border: 1px solid $hairline; overflow: hidden; }

  &__panel-header {
    display: flex; justify-content: space-between; align-items: center; padding: $spacing-sm $spacing-4; border-bottom: 1px solid $hairline;
    h3 { margin: 0; font-family: $font-text; font-size: $body-strong-size; font-weight: $body-strong-weight; display: flex; align-items: center; gap: $spacing-xxs; }
  }
  &__panel-actions { display: flex; align-items: center; gap: $spacing-xs; }
  &__round-count { font-size: $fine-print-size; color: $ink-muted-48; background: $canvas-parchment; padding: 2px 8px; border-radius: $radius-pill; }

  &__chat {
    flex: 1; overflow-y: auto; padding: $spacing-4; display: flex; flex-direction: column; gap: $spacing-sm; background: $canvas-parchment;
    &-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: $spacing-sm; color: $ink-muted-48; }
    &-msg { display: flex; gap: $spacing-xs; align-items: flex-start;
      &.user { flex-direction: row-reverse; .step3-view__chat-bubble { background: $primary; color: $on-primary; border-bottom-right-radius: $radius-xs; } }
      &.houxing { .step3-view__chat-bubble { background: $canvas; color: $ink; border: 1px solid $hairline; border-bottom-left-radius: $radius-xs; } }
      &.system { .step3-view__chat-bubble { background: transparent; color: $ink-muted-48; font-size: $caption-size; border: none; padding: 4px 0; } .step3-view__chat-avatar { opacity: 0.5; } }
    }
    &-avatar { font-size: $spacing-lg; flex-shrink: 0; }
    &-bubble { max-width: 80%; padding: 10px 14px; border-radius: $radius-sm; font-family: $font-text; font-size: $body-size; line-height: $body-leading; letter-spacing: $body-tracking; white-space: pre-wrap; word-break: break-word; }
    &-thinking { color: $ink-muted-48; }
  }


  &__send-btn { flex-shrink: 0; height: 56px; }
  &__summary-panel { display: flex; flex-direction: column; background: $canvas; border-radius: $radius-lg; border: 1px solid $hairline; overflow: hidden; }
  &__summary-icon, &__houxing-icon { font-size: 18px; }
  &__summary-content { flex: 1; padding: $spacing-4; overflow-y: auto; min-height: 200px; }
  &__doc-preview { pre { font-family: $font-text; font-size: $body-size; line-height: $body-leading; white-space: pre-wrap; word-break: break-word; margin: 0; } }
  &__doc-empty { color: $ink-muted-48; text-align: center; padding: 40px 0; }
  &__docs-path { margin-bottom: $spacing-xs; }
  &__doc-list { display: flex; flex-direction: column; gap: $spacing-xs; }
  &__doc-list-item {
    display: flex; align-items: center; gap: $spacing-sm;
    padding: $spacing-sm; border: 1px solid $hairline; border-radius: $radius-sm;
    cursor: pointer; transition: all 0.15s;
    &:hover { border-color: $primary; background: rgba($primary, 0.03); }
    &--selected { border-color: $primary; background: rgba($primary, 0.05); }
    &-name { flex: 1; font-size: $body-size; font-weight: 500; color: $ink; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  }
  &__summary-actions { padding: $spacing-sm $spacing-4; border-top: 1px solid $hairline; }
  &__action-btn { width: 100%; border-radius: $radius-pill !important; }
  &__empty-icon { font-size: 48px; }

  &__submit-section, &__qa-section, &__complete-section {
    flex: 1; display: flex; align-items: center; justify-content: center; padding: $spacing-4;
  }

  &__submit-card, &__complete-card {
    max-width: 640px; width: 100%; background: $canvas;
    border: 1px solid $hairline; border-radius: $radius-lg; text-align: center;
    h2 { font-family: $font-display; font-size: $display-md-size; margin: 0 0 $spacing-xs; }
  }

  &__qa-card {
    max-width: 1240px; width: 100%; background: $canvas;
    border: 1px solid $hairline; border-radius: $radius-lg; text-align: center;
    padding: $spacing-8;
    h2 { font-family: $font-display; font-size: $display-md-size; margin: 0 0 $spacing-xs; }
  }

  &__submit-header, &__qa-header { display: flex; align-items: center; justify-content: center; gap: $spacing-xs; h2 { margin: 0; } }
  &__submit-icon, &__qa-icon { font-size: 36px; }
  &__submit-subtitle, &__qa-subtitle { color: $ink-muted-48; margin: $spacing-xs 0 $spacing-6; }
  &__submit-preview { padding: 0 $spacing-4 $spacing-4; }
  &__submit-actions { display: flex; gap: $spacing-sm; justify-content: center; }

  &__qa-loading {
    padding: $spacing-4;
    p { color: $ink-muted-48; margin-top: $spacing-sm; }
  }

  &__qa-stream {
    max-height: 300px;
    overflow-y: auto;
    text-align: left;
    background: $canvas-parchment;
    border: 1px solid $hairline;
    border-radius: $radius-sm;
    padding: $spacing-sm;
    margin-top: $spacing-sm;
    font-size: $caption-size;
    line-height: 1.5;
    color: $ink;

    &-line {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      &--active {
        color: $primary;
      }
    }
  }

  &__qa-cursor {
    animation: blink 1s step-end infinite;
  }

  @keyframes blink {
    50% { opacity: 0; }
  }

  &__qa-dimensions {
    text-align: left;
    padding: 0 $spacing-4 $spacing-4;
  }

  &__qa-dimension {
    padding: $spacing-sm;
    margin-bottom: $spacing-xs;
    border: 1px solid $hairline;
    border-radius: $radius-sm;
    background: $canvas-parchment;

    &--pass {
      border-color: $status-done;
      background: #f0fdf4;
    }

    &--fail {
      border-color: $priority-urgent;
      background: #fef2f2;
    }

    &-header {
      display: flex;
      align-items: flex-start;
      gap: $spacing-xs;
    }

    &-icon {
      font-size: 18px;
      flex-shrink: 0;
      margin-top: 2px;
    }

    &-info {
      flex: 1;
      min-width: 0;
    }

    &-label {
      font-size: $body-strong-size;
      font-weight: $body-strong-weight;
      color: $ink;
    }

    &-desc {
      font-size: $fine-print-size;
      color: $ink-muted-48;
    }

    &-detail {
      margin-top: $spacing-xs;
      padding-top: $spacing-xs;
      border-top: 1px solid $hairline;
      font-size: $body-size;
      color: $ink;
      line-height: $body-leading;
      white-space: pre-wrap;
    }
  }

  &__qa-result {
    &--passed :deep(.el-result__icon) { --el-result-icon-color: $status-done; }
    &--failed :deep(.el-result__icon) { --el-result-icon-color: $priority-urgent; }
  }
  &__qa-waiting {
    padding: $spacing-8 $spacing-4;

    &-text {
      color: $ink-muted-48;
      margin-bottom: $spacing-4;
      font-size: $body-size;
    }
  }

  &__qa-dimension-list {
    display: flex;
    flex-direction: column;
    gap: $spacing-xs;
    margin-bottom: $spacing-6;
    text-align: left;
  }

  &__qa-dimension-item {
    display: flex;
    flex-direction: column;
    padding: $spacing-xs $spacing-sm;
    border: 1px solid $hairline;
    border-radius: $radius-sm;
    background: $canvas-parchment;

    &-label {
      font-size: $body-strong-size;
      font-weight: $body-strong-weight;
      color: $ink;
    }

    &-desc {
      font-size: $fine-print-size;
      color: $ink-muted-48;
    }
  }

  // TODO List 样式
  &__qa-todolist {
    text-align: left;
    padding: $spacing-4;
    background: $canvas-parchment;
    border-radius: $radius-sm;
    border: 1px solid $hairline;

    &-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: $spacing-sm;
      padding-bottom: $spacing-sm;
      border-bottom: 1px solid $hairline;
    }

    &-title {
      display: flex;
      align-items: center;
      gap: $spacing-xs;
      font-size: $body-strong-size;
      font-weight: $body-strong-weight;
      color: $ink;
    }

    &-icon {
      font-size: 18px;
    }
  }

  &__qa-todoitem {
    display: flex;
    align-items: flex-start;
    gap: $spacing-sm;
    padding: $spacing-sm;
    margin-bottom: $spacing-xs;
    border: 1px solid $hairline;
    border-radius: $radius-sm;
    background: $canvas;
    transition: all 0.2s;

    &--done {
      border-color: $status-done;
      background: #f0fdf4;
      opacity: 0.75;
      .step3-view__qa-todoitem-label {
        text-decoration: line-through;
        color: $ink-muted-48;
      }
    }

    &--fixing {
      border-color: $primary;
      background: #f0f7ff;
      box-shadow: 0 0 0 2px rgba($primary, 0.1);
    }

    &--verifying {
      border-color: $warning;
      background: $warning-dim;
      box-shadow: 0 0 0 2px rgba($warning, 0.1);
    }

    &--failed {
      border-color: $danger;
      background: $danger-dim;
    }

    &--pending {
      border-color: $hairline;
    }

    &-checkbox {
      flex-shrink: 0;
      margin-top: 2px;
    }

    &-body {
      flex: 1;
      min-width: 0;
    }

    &-label {
      font-size: $body-strong-size;
      font-weight: $body-strong-weight;
      color: $ink;
      margin-bottom: 2px;
    }

    &-detail {
      font-size: $fine-print-size;
      color: $ink-muted-48;
      line-height: 1.4;
      white-space: pre-wrap;
    }

    &-badge {
      flex-shrink: 0;
      margin-left: auto;
    }
  }

  &__qa-result-area {
    padding: 0 $spacing-4 $spacing-4;
  }

  &__complete-icon { font-size: 64px; margin-bottom: $spacing-sm; }
  &__complete-subtitle { color: $ink-muted-48; margin: 0 0 $spacing-4; font-size: $body-size; }
  &__complete-summary { display: flex; flex-direction: column; gap: $spacing-sm; text-align: left; }
  &__complete-item { display: flex; align-items: center; gap: $spacing-sm; padding: $spacing-sm $spacing-4; background: $canvas-parchment; border-radius: $radius-sm;
    &-icon { font-size: 24px; flex-shrink: 0; }
    &-content { flex: 1; min-width: 0; }
    &-label { font-size: $caption-size; color: $ink-muted-48; }
    &-value { font-size: $body-size; color: $ink; font-weight: 500; }
  }
  &__complete-actions { display: flex; gap: $spacing-sm; justify-content: center; }
}

.dot-pulse span {
  animation: dot-pulse 1.4s infinite; opacity: 0;
  &:nth-child(1) { animation-delay: 0s; }
  &:nth-child(2) { animation-delay: 0.2s; }
  &:nth-child(3) { animation-delay: 0.4s; }
}
@keyframes dot-pulse { 0%, 60%, 100% { opacity: 0; } 30% { opacity: 1; } }
</style>

<style lang="scss">
.step3-chat-input {
  display: flex;
  flex-shrink: 0;
  gap: $spacing-xs;
  padding: $spacing-sm $spacing-4;
  border-top: 1px solid $hairline;
  align-items: flex-end;
  background: $canvas;

  .step3-view__send-btn {
    flex-shrink: 0;
    height: 56px;
  }
}
</style>
