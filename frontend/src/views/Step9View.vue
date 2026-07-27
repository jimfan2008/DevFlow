<template>
  <div class="step9-view" v-loading="loading">
    <div class="step9-view__header">
      <div class="step9-view__header-left">
        <el-button :icon="ArrowLeft" text @click="goBack">返回</el-button>
        <div>
          <h1>第九步：编写功能代码</h1>
          <p class="step9-view__subtitle">{{ projectName }} · 后发蜂群并行编写 {{ totalTasks }} 个文件</p>
        </div>
      </div>
      <div class="step9-view__header-right">
        <el-tag :type="statusTag" effect="dark" size="large">{{ statusLabel }}</el-tag>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon closable class="step9-view__alert" />

    <!-- loading: 自动启动蜂群中 -->
    <div v-if="(stepStatus === 'pending' || stepStatus === 'in_progress') && taskStatesArray.length === 0 && !executing" class="step9-view__loading-start">
      <div class="step9-view__loading-icon">🐝</div>
      <h2>正在启动后发蜂群...</h2>
      <p>{{ streamStatus || '正在准备并行执行环境' }}</p>
      <el-progress :percentage="100" :stroke-width="4" status="warning" indeterminate style="max-width:300px; margin:12px auto" />
    </div>

    <!-- executing / results: agent grid + TODO sidebar -->
    <div v-if="taskStatesArray.length > 0" class="step9-view__executing">
      <div class="step9-view__executing-header">
        <div class="step9-view__card-icon">🐝</div>
        <div class="step9-view__executing-info">
          <h2>后发蜂群并行编写功能代码</h2>
          <p class="step9-view__executing-status">{{ streamStatus || '蜂群正在工作中...' }}</p>
        </div>
        <div v-if="stepStatus === 'completed'" class="step9-view__executing-header-right">
          <el-tag type="success" effect="dark" size="large">✅ 已完成</el-tag>
        </div>
      </div>

      <el-alert v-if="stuckWarning" :title="stuckWarning" type="warning" show-icon closable class="step9-view__alert" />
      <el-alert v-if="backendError" :title="backendError" type="error" show-icon closable class="step9-view__alert" @close="backendError = ''" />

      <div class="step9-view__body">
        <!-- Left: Agent Grid -->
        <div class="step9-view__main">
          <div v-if="taskStatesArray.length === 0" class="step9-view__empty-agents">
            <p>{{ streamStatus || '⏳ 等待后发解析代码计划并创建子任务...' }}</p>
            <el-progress :percentage="100" :stroke-width="4" status="warning" indeterminate style="max-width:300px; margin:12px auto" />
          </div>

          <!-- Connected Agents Panel -->
          <div v-if="connectedAgents.length > 0" class="step9-view__connected-agents">
            <h4>🐝 已连接Agent</h4>
            <div class="step9-view__agent-chips">
              <div v-for="a in connectedAgents" :key="a.name" class="step9-view__agent-chip" :class="'role-' + a.role">
                <span class="step9-view__agent-chip-icon">✍️</span>
                <span class="step9-view__agent-chip-name">{{ a.name }}</span>
                <el-tag size="small" :type="a.role === 'writer' ? 'warning' : 'primary'">{{ a.agentType }}</el-tag>
              </div>
            </div>
          </div>

          <div v-if="taskStatesArray.length > 0" class="step9-view__agents">
            <div
              v-for="task in taskStatesArray"
              :key="task.index"
              class="step9-view__agent-panel"
              :class="'status-' + task.status"
            >
              <div class="step9-view__agent-header">
                <span class="step9-view__agent-index">#{{ task.index }}</span>
                <span class="step9-view__agent-name">{{ task.name }}</span>
                <el-tag
                  :type="agentTagType[task.status]"
                  size="small"
                  effect="dark"
                >{{ agentStatusLabel[task.status] }}</el-tag>
              </div>

              <div class="step9-view__agent-body">
                <div class="step9-view__agent-line">
                  <span class="step9-view__agent-label">✍️ 编写Agent</span>
                  <span class="step9-view__agent-value">{{ task.writerAgent || '等待分配...' }}</span>
                </div>
                <div class="step9-view__agent-line" v-if="task.writerResponse">
                  <el-button text size="small" @click="task.showWriterResponse = !task.showWriterResponse">
                    {{ task.showWriterResponse ? '收起' : '📄 编写响应' }}
                  </el-button>
                </div>
                <div v-if="task.showWriterResponse && task.writerResponse" class="step9-view__response-box">
                  <pre>{{ task.writerResponse }}</pre>
                </div>
                <div class="step9-view__agent-line" v-if="task.attempts > 0">
                  <span class="step9-view__agent-label">🔄 轮次</span>
                  <span class="step9-view__agent-value">{{ task.attempts }}/{{ MAX_ATTEMPTS }}</span>
                </div>
              </div>
              <div v-if="task.message && !task.writerPrompt" class="step9-view__agent-msg">{{ task.message }}</div>
              <div class="step9-view__agent-bar">
                <el-progress
                  v-if="task.status === 'writing' || task.status === 'testing'"
                  :percentage="100" :stroke-width="3" status="warning" indeterminate
                />
                <el-progress
                  v-else-if="task.status === 'passed'"
                  :percentage="100" :stroke-width="3" status="success"
                />
                <el-progress
                  v-else-if="task.status === 'failed'"
                  :percentage="100" :stroke-width="3" status="exception"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Right: TODO Sidebar -->
        <div class="step9-view__sidebar">
          <div class="step9-view__sidebar-card">
            <h3>📋 TODO 清单</h3>
            <div class="step9-view__stats">
              <div class="step9-view__stat step9-view__stat--total">
                <span class="step9-view__stat-label">总计</span>
                <span class="step9-view__stat-value">{{ totalTasks }}</span>
              </div>
              <div class="step9-view__stat step9-view__stat--passed">
                <span class="step9-view__stat-label">✅ 通过</span>
                <span class="step9-view__stat-value">{{ passedCount }}</span>
              </div>
              <div class="step9-view__stat step9-view__stat--failed">
                <span class="step9-view__stat-label">❌ 失败</span>
                <span class="step9-view__stat-value">{{ failedCount }}</span>
              </div>
              <div class="step9-view__stat step9-view__stat--active">
                <span class="step9-view__stat-label">⏳ 进行中</span>
                <span class="step9-view__stat-value">{{ activeCount }}</span>
              </div>
              <div class="step9-view__stat step9-view__stat--pending">
                <span class="step9-view__stat-label">⏸️ 待执行</span>
                <span class="step9-view__stat-value">{{ pendingCount }}</span>
              </div>
            </div>
            <el-progress :percentage="progressPercent" :stroke-width="8" :color="progressColor" class="step9-view__progress-bar" />
            <div class="step9-view__task-list" ref="taskListRef">
              <div
                v-for="task in pendingTasksArray"
                :key="task.index"
                class="step9-view__task-item"
                :class="'status-' + task.status"
              >
                <span class="step9-view__task-icon">{{ taskIcon[task.status] }}</span>
                <span class="step9-view__task-name">{{ task.name }}</span>
                <span v-if="task.attempts > 0" class="step9-view__task-attempt">{{ task.attempts }}/{{ MAX_ATTEMPTS }}</span>
              </div>
              <div v-if="taskStatesArray.length === 0" class="step9-view__task-empty">{{ streamStatus || '暂无子任务' }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="step9-view__executing-actions">
        <div v-if="failedCount > 0" class="step9-view__resume-action" style="margin-bottom: 16px;">
          <el-button type="primary" size="large" :loading="executing" @click="handleExecute">
            🔄 续跑未通过子任务
          </el-button>
        </div>
        <el-button
          v-if="stuckWarning || backendError"
          type="danger"
          size="large"
          :loading="restarting"
          @click="handleRestart"
        >
          🔄 强制重新执行
        </el-button>
      </div>

      <el-collapse class="step9-view__stage-collapse">
        <el-collapse-item title="📋 完整执行日志" name="log">
          <div class="step9-view__stage-log">
            <div v-for="(msg, i) in stageLog" :key="i" class="step9-view__progress-msg" :class="msg.type">
              <span v-if="msg.type === 'stage'">📌</span>
              <span v-else-if="msg.type === 'progress'">⏳</span>
              <span v-else-if="msg.type === 'done'">✅</span>
              <span v-else>ℹ️</span>
              {{ msg.message }}
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- Code preview -->
    <div v-if="taskStatesArray.length > 0" class="step9-view__tabs">
      <el-tabs v-model="activeDocTab">
        <el-tab-pane label="📄 功能代码" name="code">
          <div class="step9-view__doc-content" v-if="codeContent">
            <pre>{{ codeContent }}</pre>
          </div>
          <el-empty v-else description="暂无代码内容" />
        </el-tab-pane>
        <el-tab-pane label="📊 执行统计" name="stats">
          <div class="step9-view__stats-detail" v-if="taskStatesArray.length">
            <div class="step9-view__stats-grid">
              <div class="step9-view__stats-item"><span>总文件数</span><strong>{{ totalTasks }}</strong></div>
              <div class="step9-view__stats-item"><span>✅ 通过</span><strong class="text-success">{{ passedCount }}</strong></div>
              <div class="step9-view__stats-item"><span>❌ 失败</span><strong class="text-danger">{{ failedCount }}</strong></div>
            </div>
          </div>
          <el-empty v-else description="暂无统计数据" />
        </el-tab-pane>
      </el-tabs>
    </div>

    <div v-if="stepStatus === 'error'" class="step9-view__resume-section">
      <el-divider />
      <p class="step9-view__error-hint">{{ backendError || '部分子任务执行失败' }}</p>
      <div class="step9-view__actions">
        <el-button size="large" @click="goBack">返回项目</el-button>
        <el-button type="danger" size="large" :loading="executing" @click="handleExecute">🔄 强制重新执行</el-button>
      </div>
    </div>

    <div v-if="stepStatus === 'completed'" class="step9-view__complete-actions">
      <el-divider />
      <div class="step9-view__actions">
        <el-button size="large" @click="goBack">返回项目</el-button>
        <el-button type="primary" size="large" @click="goToNext">进入下一步 ➜</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { workflowApi } from '@/api/modules/workflow'

const MAX_ATTEMPTS = 10

const props = defineProps<{ projectId: string }>()
const router = useRouter()
const route = useRoute()
const projectName = ref((route.query.name as string) || '未命名项目')

const loading = ref(false)
const executing = ref(false)
const error = ref('')
const stepStatus = ref<'pending' | 'in_progress' | 'qa_review' | 'completed' | 'error'>('pending')
const streamStatus = ref('')
const stageLog = ref<{ type: string; message: string }[]>([])
const stuckWarning = ref('')
const backendError = ref('')
const restarting = ref(false)
const codeContent = ref('')
const activeDocTab = ref('code')

type TaskStatus = 'pending' | 'writing' | 'testing' | 'passed' | 'failed'

interface TaskState {
  index: number
  name: string
  writerAgent: string
  status: TaskStatus
  attempts: number
  message: string
  writerPrompt: string
  showWriterPrompt: boolean
  writerResponse: string
  showWriterResponse: boolean
}

const taskStates = ref<Record<number, TaskState>>({})
const taskStatesArray = computed(() =>
  Object.values(taskStates.value).sort((a, b) => a.index - b.index)
)

const connectedAgents = ref<{name: string; role: string; agentType: string}[]>([])
const writerAgentsList = computed(() => connectedAgents.value.filter(a => a.role === 'writer'))

const totalTasks = computed(() => taskStatesArray.value.length)
const passedCount = computed(() => taskStatesArray.value.filter(t => t.status === 'passed').length)
const failedCount = computed(() => taskStatesArray.value.filter(t => t.status === 'failed').length)
const activeCount = computed(() => taskStatesArray.value.filter(t => t.status === 'writing' || t.status === 'testing').length)
const pendingCount = computed(() => taskStatesArray.value.filter(t => t.status === 'pending').length)
const pendingTasksArray = computed(() =>
  taskStatesArray.value.filter(t => t.status !== 'passed')
)

const progressPercent = computed(() => {
  if (totalTasks.value === 0) return 0
  return Math.round((passedCount.value + failedCount.value) / totalTasks.value * 100)
})

const progressColor = computed(() => {
  if (failedCount.value > 0) return '#f56c6c'
  if (progressPercent.value === 100) return '#67c23a'
  return '#409eff'
})

const agentTagType: Record<string, string> = {
  pending: 'info', writing: 'warning', testing: 'primary',
  passed: 'success', failed: 'danger',
}
const agentStatusLabel: Record<string, string> = {
  pending: '待执行', writing: '✍️ 编写中', testing: '🔍 验证中',
  passed: '✅ 通过', failed: '❌ 失败',
}
const taskIcon: Record<string, string> = {
  pending: '⏳', writing: '✍️', testing: '🔍',
  passed: '✅', failed: '❌',
}

const statusTag = computed(() => {
  const map: Record<string, string> = { pending: 'info', in_progress: 'warning', qa_review: 'warning', completed: 'success', error: 'danger' }
  return map[stepStatus.value] || 'info'
})
const statusLabel = computed(() => {
  const map: Record<string, string> = { pending: '待执行', in_progress: '执行中', qa_review: '待检验', completed: '已完成', error: '出错' }
  return map[stepStatus.value] || stepStatus.value
})

// ── WebSocket ──
let ws: WebSocket | null = null
let wsTimer: ReturnType<typeof setTimeout> | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null
const STUCK_TIMEOUT_MS = 120000
const taskListRef = ref<HTMLElement | null>(null)

function resetStuckTimer() {
  if (wsTimer) { clearTimeout(wsTimer); wsTimer = null }
  wsTimer = setTimeout(() => {
    if (stepStatus.value === 'in_progress') {
      stuckWarning.value = '⚠️ 长时间未收到Agent实时消息，可能已中断。请点"强制重新执行"恢复。'
    }
  }, STUCK_TIMEOUT_MS)
}

function clearAllTimers() {
  if (wsTimer) { clearTimeout(wsTimer); wsTimer = null }
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

function getWsUrl(): string {
  const token = localStorage.getItem('access_token') || ''
  const port = import.meta.env.VITE_BACKEND_PORT || '9000'
  const base = import.meta.env.VITE_WS_BASE_URL || `ws://${location.hostname}:${port}`
  return `${base}/api/step9/progress/${props.projectId}?token=${encodeURIComponent(token)}`
}

function parseStep9Message(msg: { type: string; message?: string; content?: string; subtask_names?: string[]; subtask_indices?: number[] }) {
  const txt = msg.message || ''
  if (!txt && !msg.subtask_names) return

  // Update display
  if (txt) {
    streamStatus.value = txt
    stageLog.value.push({ type: 'progress', message: txt })
  }

  // ── 子任务列表（创建卡片） ──
  if (msg.subtask_names && Array.isArray(msg.subtask_names)) {
    const indices: number[] = msg.subtask_indices || msg.subtask_names.map((_, i) => i + 1)
    for (let i = 0; i < msg.subtask_names.length; i++) {
      const idx = indices[i]
      const name = msg.subtask_names[i]
      if (!taskStates.value[idx]) {
        taskStates.value[idx] = {
          index: idx, name,
          writerAgent: '', status: 'pending',
          attempts: 0, message: '',
          writerPrompt: '', showWriterPrompt: false,
          writerResponse: '', showWriterResponse: false,
        }
      }
    }
    return
  }

  // ── 提取子任务名 [name] ──
  const sname = extractBracketName(txt)
  if (!sname) return
  let task = Object.values(taskStates.value).find(t => t.name === sname)
  if (!task) return

  task.message = txt

  // ── 正在编写 ──
  const writerMatch = txt.match(/✍️.*?编写（第(\d+)轮）/)
  if (writerMatch) {
    task.status = 'writing'
    task.attempts = parseInt(writerMatch[1])
    const agentExtract = txt.match(/\] (.+?) 编写/)
    if (agentExtract) task.writerAgent = agentExtract[1].trim()
    scrollTaskList()
    return
  }

  // ── 正在检验 ──
  if (txt.includes('检验中')) {
    task.status = 'testing'
    scrollTaskList()
    return
  }

  // ── 通过 ──
  const passMatch = txt.match(/✅.*?通过（第(\d+)轮）/)
  if (passMatch) {
    task.status = 'passed'
    task.attempts = parseInt(passMatch[1])
    scrollTaskList()
    return
  }

  // ── 未通过 ──
  if (txt.includes('⚠️') && txt.includes('未通过')) {
    task.status = 'writing'
    return
  }

  // ── 10轮均未通过 ──
  if (txt.includes('❌') && txt.includes('均未通过')) {
    task.status = 'failed'
    scrollTaskList()
    return
  }
}

function extractBracketName(msg: string): string | null {
  const m = msg.match(/\[([^\]]+)\]/)
  return m ? m[1] : null
}

let wsReadyResolve: (() => void) | null = null

function connectWs() {
  if (ws) { ws.onclose = null; ws.close(); ws = null }
  wsReadyResolve = null
  try {
    ws = new WebSocket(getWsUrl())
    ws.onopen = () => {
      if (wsReadyResolve) { wsReadyResolve(); wsReadyResolve = null }
    }
    ws.onmessage = (event) => {
      try {
        resetStuckTimer()
        stuckWarning.value = ''
        const msg = JSON.parse(event.data)
        if (msg.type === 'step9' || msg.type === 'stage' || msg.type === 'progress') {
          if (msg.message || msg.subtask_names) parseStep9Message(msg)
        } else if (msg.type === 'agent_online') {
          if (msg.name && !connectedAgents.value.find(a => a.name === msg.name)) {
            connectedAgents.value.push({name: msg.name, role: msg.role, agentType: msg.agent_type})
          }
        } else if (msg.type === 'content') {
          // handle incremental content
        } else if (msg.type === 'done') {
          if (msg.message) {
            stageLog.value.push({ type: 'done', message: msg.message })
            streamStatus.value = msg.message
          }
          clearAllTimers()
          executing.value = false
          setTimeout(async () => {
            try {
              await loadStatus()
              const res = await workflowApi.getStatus(props.projectId) as any
              const stepRow = (res?.data || res)?.steps?.['9']
              if (stepRow?.status === 'completed') {
                router.push({ name: 'Step10', params: { projectId: props.projectId }, query: { name: projectName.value } })
              }
            } catch {}
          }, 2000)
        } else if (msg.type === 'error') {
          if (msg.message) stageLog.value.push({ type: 'error', message: msg.message })
          backendError.value = msg.message || '后端执行出错'
          stepStatus.value = 'error'
          clearAllTimers()
          executing.value = false
        }
      } catch {}
    }
    ws.onclose = () => { ws = null; wsReadyResolve = null }
    ws.onerror = () => { ws = null; wsReadyResolve = null }
  } catch {}
}

async function waitForWs(): Promise<void> {
  if (ws && ws.readyState === WebSocket.OPEN) return
  return new Promise((resolve) => {
    wsReadyResolve = resolve
  })
}

function startPolling() {
  let emptyCount = 0
  pollTimer = setInterval(async () => {
    try {
      const res = await workflowApi.getStatus(props.projectId) as any
      const data = res?.data || res
      const s9 = data?.step9 || {}

      // Restore subtask results
      if (s9.subtask_results) {
        for (const sr of s9.subtask_results) {
          const task = taskStates.value[sr.index]
          const resolvedStatus: string = (sr.status === 'passed' || sr.status === 'done') ? 'passed' : sr.status === 'failed' ? 'failed' : 'pending'
          if (task) {
            task.status = resolvedStatus
            task.attempts = sr.attempts || 0
            if (sr.writer) task.writerAgent = sr.writer
          } else {
            taskStates.value[sr.index] = {
              index: sr.index, name: sr.name,
              writerAgent: sr.writer || '', status: resolvedStatus,
              attempts: sr.attempts || 0, message: '',
              writerPrompt: '', showWriterPrompt: false,
              writerResponse: '', showWriterResponse: false,
            }
          }
        }
      }

      // Initialize task cards from total_subtask_names (in case WS broadcast was missed)
      if (s9.total_subtask_names && s9.total_subtask_names.length > 0) {
        const indices: number[] = s9.total_subtask_indices || s9.total_subtask_names.map((_, i) => i + 1)
        for (let i = 0; i < s9.total_subtask_names.length; i++) {
          const idx = indices[i]
          const name = s9.total_subtask_names[i]
          if (!taskStates.value[idx]) {
            taskStates.value[idx] = {
              index: idx, name,
              writerAgent: '', status: 'pending',
              attempts: 0, message: '',
              writerPrompt: '', showWriterPrompt: false,
              writerResponse: '', showWriterResponse: false,
            }
          }
        }
      }

      if (s9.code && s9.code.trim().length > 50) {
        codeContent.value = s9.code
      }

      const stepRow = data?.steps?.['9']
      if (stepRow?.status === 'completed') {
        stepStatus.value = 'completed'
        executing.value = false
        streamStatus.value = '✅ 功能代码已生成'
        clearAllTimers()
      } else if (stepRow?.status === 'qa_review') {
        stepStatus.value = 'qa_review'
        executing.value = false
        clearAllTimers()
      } else if (s9.status === 'error') {
        backendError.value = s9.message || '后端任务执行失败'
        streamStatus.value = '❌ 执行失败'
        stepStatus.value = 'error'
        clearAllTimers()
      } else if (data?.steps?.['9']?.status === 'in_progress') {
        emptyCount = 0
      } else {
        emptyCount++
        if (emptyCount >= 6) {
          stuckWarning.value = '⚠️ 后端无响应超过30秒，可能已中断。'
        }
      }
    } catch {
      emptyCount++
      if (emptyCount >= 6) {
        stuckWarning.value = '⚠️ 无法连接后端超过30秒。'
      }
    }
  }, 5000)
}

function scrollTaskList() {
  nextTick(() => {
    if (taskListRef.value) {
      taskListRef.value.scrollTop = taskListRef.value.scrollHeight
    }
  })
}

// ── Status Loading ──
async function loadStatus() {
  loading.value = true
  try {
    projectName.value = (route.query.name as string) || ''
    const res = await workflowApi.getStatus(props.projectId) as any
    const data = res?.data || res
    const steps = data?.steps || {}
    const stepRow = steps['9'] || {}
    stepStatus.value = stepRow.status || 'pending'

    // Load step9 specific artifacts
    let s9 = data?.step9 || {}

    if (s9.code && s9.code.trim().length > 50) {
      codeContent.value = s9.code
    }

    // ── 预创建所有子任务占位 ──
    if (s9.total_subtask_names && s9.total_subtask_names.length > 0) {
      for (let i = 0; i < s9.total_subtask_names.length; i++) {
        const idx = i + 1
        const name = s9.total_subtask_names[i]
        if (!taskStates.value[idx]) {
          taskStates.value[idx] = {
            index: idx, name,
            writerAgent: '', status: 'pending',
            attempts: 0, message: '',
            writerPrompt: '', showWriterPrompt: false,
            writerResponse: '', showWriterResponse: false,
          }
        }
      }
    }

    // ── 恢复子任务状态 ──
    if (s9.subtask_results) {
      for (const sr of s9.subtask_results) {
        const existing = taskStates.value[sr.index]
        const resolvedStatus: string = (sr.status === 'passed' || sr.status === 'done') ? 'passed' : sr.status === 'failed' ? 'failed' : 'pending'
        if (existing) {
          existing.status = resolvedStatus
          existing.attempts = sr.attempts || 0
          if (sr.writer) existing.writerAgent = sr.writer
        } else {
          taskStates.value[sr.index] = {
            index: sr.index, name: sr.name,
            writerAgent: sr.writer || '', status: resolvedStatus,
            attempts: sr.attempts || 0, message: '',
            writerPrompt: '', showWriterPrompt: false,
            writerResponse: '', showWriterResponse: false,
          }
        }
      }
    }

    if (s9.message) {
      stageLog.value.push({ type: 'stage', message: s9.message })
    }

    if (stepStatus.value === 'pending') {
      if (s9.subtask_results && s9.subtask_results.length > 0) {
        const allPassed = s9.subtask_results.every(sr => sr.status === 'passed')
        if (allPassed) {
          stageLog.value.push({ type: 'stage', message: `♻️ 从数据库恢复 ${s9.subtask_results.length} 个子任务状态` })
          streamStatus.value = '✅ 所有子任务已通过'
          stepStatus.value = 'completed'
        } else {
          const passedCount_v = s9.subtask_results.filter(sr => sr.status === 'passed').length
          stageLog.value.push({ type: 'stage', message: `♻️ 恢复 ${passedCount_v} 个已通过，启动续跑...` })
          streamStatus.value = '♻️ 自动续跑...'
          setTimeout(() => handleExecute(), 500)
        }
      } else {
        stageLog.value.push({ type: 'stage', message: '🚀 准备启动后发蜂群编写功能代码...' })
        setTimeout(() => handleExecute(), 300)
      }
    }

    if (stepStatus.value === 'in_progress') {
      const allPassed = s9.subtask_results && s9.subtask_results.length > 0 && s9.subtask_results.every(sr => sr.status === 'passed')
      if (allPassed) {
        stepStatus.value = 'completed'
        streamStatus.value = '✅ 所有子任务已通过'
        clearAllTimers()
      } else {
        connectWs()
        startPolling()
        resetStuckTimer()
        const hasFailedOrPending = s9.subtask_results && s9.subtask_results.some(sr => sr.status === 'failed' || sr.status === 'pending')
        if (hasFailedOrPending) {
          stageLog.value.push({ type: 'stage', message: '🔄 检测到有未通过的子任务，正在自动续跑...' })
          setTimeout(() => handleExecute(), 500)
        }
      }
    }
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

// ── Execute ──
async function handleExecute() {
  executing.value = true
  restarting.value = false
  error.value = ''
  backendError.value = ''
  stuckWarning.value = ''
  codeContent.value = ''
  stageLog.value = [{ type: 'stage', message: '🐝 正在启动后发蜂群...' }]
  streamStatus.value = '🐝 正在启动后发蜂群...'
  stepStatus.value = 'in_progress'
  connectedAgents.value = []
  clearAllTimers()

  connectWs()
  await waitForWs()
  startPolling()
  resetStuckTimer()

  try {
    const res = await workflowApi.executeStep(props.projectId, 9) as any
    if (res?.code === 0) {
      streamStatus.value = '🐝 后发蜂群已启动，等待执行...'
      stageLog.value.push({ type: 'stage', message: '📡 WebSocket已连接，后端子任务创建中...' })
    } else {
      error.value = res?.message || '启动失败'
      stepStatus.value = 'pending'
      executing.value = false
      clearAllTimers()
    }
  } catch (e: any) {
    error.value = e?.message || '与后端通信失败'
    stepStatus.value = 'pending'
    executing.value = false
    clearAllTimers()
  }
}

async function handleRestart() {
  restarting.value = true
  backendError.value = ''
  stuckWarning.value = ''
  error.value = ''
  clearAllTimers()
  if (ws) { ws.onclose = null; ws.close(); ws = null }
  stepStatus.value = 'in_progress'
  executing.value = true
  streamStatus.value = '♻️ 强制重新执行...'
  stageLog.value = [{ type: 'stage', message: '♻️ 强制重新执行 step9...' }]
  taskStates.value = {}
  connectedAgents.value = []
  connectWs()
  await waitForWs()
  startPolling()
  resetStuckTimer()
  try {
    await workflowApi.executeStep(props.projectId, 9)
  } catch (e: any) {
    error.value = e?.message || '重试失败'
  } finally {
    restarting.value = false
  }
}

function goBack() { router.push({ name: 'ProjectDetail', params: { projectId: props.projectId } }) }
function goToNext() { router.push({ name: 'Step10', params: { projectId: props.projectId }, query: { name: projectName.value } }) }

onMounted(() => loadStatus())
onUnmounted(() => {
  clearAllTimers()
  if (ws) { ws.onclose = null; ws.close(); ws = null }
})
</script>

<style scoped lang="scss">
.step9-view {
  max-width: 1200px; margin: 0 auto; padding: 32px 24px;

  &__header {
    display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px;
    &-left { display: flex; align-items: flex-start; gap: 16px; h1 { margin: 0; font-size: 24px; font-weight: 600; } }
  }
  &__subtitle { margin: 4px 0 0; color: $text-muted; font-size: 14px; }
  &__alert { margin-bottom: 16px; }

  &__loading-start {
    text-align: center; padding: 60px 24px;
    background: $glass-bg; backdrop-filter: $frosted-blur;
    border: 1px solid $glass-border; border-radius: 12px;
    h2 { margin: 16px 0 8px; font-size: 20px; font-weight: 600; color: $text-primary; }
    p { color: $text-muted; margin: 0 0 12px; }
    &-icon { font-size: 48px; line-height: 1; }
  }

  &__executing {
    background: $glass-bg; backdrop-filter: $frosted-blur;
    border: 1px solid $glass-border; border-radius: 12px; padding: 20px;
    &-header { display: flex; align-items: center; gap: 16px; margin-bottom: 16px;
      .step9-view__card-icon { font-size: 36px; }
      h2 { margin: 0; font-size: 18px; font-weight: 600; color: $text-primary; }
    }
    &-status { font-size: 14px; color: $primary; font-weight: 500; margin: 4px 0 0 !important; }
  }

  &__body { display: flex; gap: 16px; align-items: flex-start; }
  &__main { flex: 1; min-width: 0; }

  &__empty-agents { text-align: center; padding: 40px 20px; color: $text-muted; p { font-size: 15px; margin: 0; } }

  &__connected-agents {
    margin-bottom: 12px; padding: 10px 12px; background: rgba(255, 255, 255, 0.04); border-radius: 8px;
    h4 { margin: 0 0 8px; font-size: 14px; font-weight: 600; color: $text-primary; }
  }
  &__agent-chips { display: flex; flex-wrap: wrap; gap: 6px; }
  &__agent-chip {
    display: flex; align-items: center; gap: 4px; padding: 4px 10px;
    border-radius: 16px; font-size: 12px;
    border: 1px solid $glass-border; background: $glass-bg; backdrop-filter: $frosted-blur;
    &.role-writer { border-color: $warning; background: $warning-dim; }
    &-icon { font-size: 14px; }
    &-name { font-weight: 500; color: $text-primary; }
  }

  &__agents { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; }

  &__agent-panel {
    background: $glass-bg; backdrop-filter: $frosted-blur;
    border: 1px solid $glass-border; border-radius: 10px; padding: 10px 12px;
    transition: all 0.3s ease;
    &.status-writing { border-color: $warning; background: $warning-dim; }
    &.status-testing { border-color: $primary; background: $primary-dim; }
    &.status-passed { border-color: $secondary; background: $secondary-dim; }
    &.status-failed { border-color: $danger; background: $danger-dim; }
    &.status-pending { border-color: $border-default; background: rgba(255, 255, 255, 0.03); }
  }

  &__agent-header { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
  &__agent-index { font-size: 11px; color: $text-muted; background: rgba(255, 255, 255, 0.06); padding: 1px 5px; border-radius: 3px; min-width: 22px; text-align: center; }
  &__agent-name { font-weight: 600; font-size: 13px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: $text-primary; }

  &__agent-body { margin-bottom: 4px; }
  &__agent-line { display: flex; align-items: center; gap: 4px; font-size: 12px; margin-bottom: 2px; }
  &__agent-label { color: $text-muted; min-width: 48px; font-size: 11px; }
  &__agent-value { color: $text-primary; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  &__agent-msg { font-size: 11px; color: $text-secondary; line-height: 1.3; margin-bottom: 4px; }
  &__agent-bar { margin-top: 4px; }

  // ── Right: TODO sidebar ──
  &__sidebar { width: 280px; flex-shrink: 0; }
  &__sidebar-card {
    background: $glass-bg; backdrop-filter: $frosted-blur;
    border: 1px solid $glass-border; border-radius: 12px; padding: 16px;
    position: sticky; top: 16px;
    h3 { margin: 0 0 12px; font-size: 16px; font-weight: 600; color: $text-primary; }
  }

  &__stats { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 12px; }
  &__stat {
    padding: 8px 10px; border-radius: 6px; border: 1px solid $border-subtle;
    display: flex; justify-content: space-between; align-items: center;
    font-size: 13px; color: $text-secondary;
    &--total { background: rgba(255, 255, 255, 0.03); grid-column: 1 / -1; }
    &--passed { background: $secondary-dim; border-color: rgba(52, 211, 153, 0.3); }
    &--failed { background: $danger-dim; border-color: rgba(239, 68, 68, 0.3); }
    &--active { background: $primary-dim; border-color: rgba(0, 212, 255, 0.3); }
    &--pending { background: rgba(255, 255, 255, 0.03); border-color: $border-default; }
    &-value { font-weight: 700; font-size: 16px; color: $text-primary; }
  }

  &__progress-bar { margin-bottom: 12px; }
  &__task-list { max-height: 400px; overflow-y: auto; }
  &__task-item {
    display: flex; align-items: center; gap: 6px; padding: 6px 8px;
    border-radius: 4px; font-size: 12px; margin-bottom: 3px;
    border-left: 3px solid transparent; color: $text-secondary;
    &.status-passed { background: $secondary-dim; border-color: $secondary; }
    &.status-failed { background: $danger-dim; border-color: $danger; }
    &.status-writing, &.status-testing { background: $warning-dim; border-color: $warning; }
    &.status-pending { border-color: $border-default; }
  }
  &__task-icon { font-size: 14px; }
  &__task-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  &__task-attempt { font-size: 10px; color: $text-muted; }
  &__task-empty { text-align: center; color: $text-disabled; padding: 20px 0; font-size: 13px; }

  &__response-box {
    grid-column: 1 / -1; margin: 4px 0 8px 0;
    pre {
      background: #f0f9eb; border: 1px solid #b3e19d; border-radius: 4px;
      padding: 8px; font-size: 11px; line-height: 1.4; max-height: 300px;
      overflow-y: auto; white-space: pre-wrap; word-break: break-all; margin: 0;
    }
  }

  &__executing-actions { display: flex; justify-content: center; gap: 12px; margin-top: 16px; }
  &__stage-collapse { margin-top: 12px; :deep(.el-collapse-item__header) { font-size: 13px; } }
  &__stage-log { max-height: 200px; overflow-y: auto; }
  &__progress-msg {
    padding: 4px 10px; margin-bottom: 3px; border-radius: 4px; font-size: 12px;
    line-height: 1.4; background: rgba(255, 255, 255, 0.03); border: 1px solid $border-subtle; color: $text-secondary;
    &.stage { border-left: 3px solid $warning; }
    &.done { border-left: 3px solid $secondary; background: $secondary-dim; }
    &.error { border-left: 3px solid $danger; background: $danger-dim; }
  }

  &__tabs { background: $glass-bg; backdrop-filter: $frosted-blur; border: 1px solid $glass-border; border-radius: 10px; padding: 16px; margin-top: 12px; }
  &__doc-content { max-height: 600px; overflow-y: auto;
    pre { white-space: pre-wrap; word-break: break-word; font-size: 13px; line-height: 1.6; margin: 0; }
  }
  &__stats-detail { padding: 8px 0; }
  &__stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  &__stats-item {
    padding: 12px 16px; background: rgba(255, 255, 255, 0.04); border-radius: 6px;
    display: flex; justify-content: space-between; align-items: center;
    font-size: 14px; color: $text-secondary;
    strong { font-size: 18px; color: $text-primary; }
  }

  &__resume-section { margin-top: 24px; }
  &__error-hint { text-align: center; color: #f56c6c; font-size: 14px; margin: 0 0 16px; }
  &__complete-actions { margin-top: 24px; }
  &__actions { display: flex; justify-content: center; gap: 12px; }
}

.text-success { color: #67c23a; }
.text-danger { color: #f56c6c; }
</style>
