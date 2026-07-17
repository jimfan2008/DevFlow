<template>
  <div class="step7-view" v-loading="loading">
    <div class="step7-view__header">
      <div class="step7-view__header-left">
        <el-button :icon="ArrowLeft" text @click="goBack">返回</el-button>
        <div>
          <h1>第七步：编写TDD测试用例</h1>
          <p class="step7-view__subtitle">{{ projectName }} · 后发蜂群并行执行 {{ totalTasks }} 个子任务</p>
        </div>
      </div>
      <div class="step7-view__header-right">
        <el-tag :type="statusTag" effect="dark" size="large">{{ statusLabel }}</el-tag>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon closable class="step7-view__alert" />

    <!-- loading: 自动启动蜂群中（取代原中间页，直接进入蜂群执行视图） -->
    <div v-if="(stepStatus === 'pending' || stepStatus === 'in_progress') && taskStatesArray.length === 0 && !executing" class="step7-view__loading-start">
      <div class="step7-view__loading-icon">🐝</div>
      <h2>正在启动后发蜂群...</h2>
      <p>{{ streamStatus || '正在准备并行执行环境' }}</p>
      <el-progress :percentage="100" :stroke-width="4" status="warning" indeterminate style="max-width:300px; margin:12px auto" />
    </div>

    <!-- executing / results: agent grid + TODO sidebar (只要有任务状态就显示) -->
    <div v-if="taskStatesArray.length > 0" class="step7-view__executing">
      <div class="step7-view__executing-header">
        <div class="step7-view__card-icon">🐝</div>
        <div class="step7-view__executing-info">
          <h2>后发蜂群并行执行</h2>
          <p class="step7-view__executing-status">{{ streamStatus || '蜂群正在工作中...' }}</p>
        </div>
        <div v-if="stepStatus === 'completed'" class="step7-view__executing-header-right">
          <el-tag type="success" effect="dark" size="large">✅ 已完成</el-tag>
        </div>
      </div>

      <el-alert
        v-if="stuckWarning"
        :title="stuckWarning"
        type="warning"
        show-icon
        closable
        class="step7-view__alert"
      />
      <el-alert
        v-if="backendError"
        :title="backendError"
        type="error"
        show-icon
        closable
        class="step7-view__alert"
        @close="backendError = ''"
      />

      <!-- TDD计划预览 -->
      <div v-if="tddPlan" class="step7-view__tdd-plan">
        <el-collapse>
          <el-collapse-item title="📄 TDD计划文档" name="tdd-plan">
            <pre class="step7-view__tdd-plan-content">{{ tddPlan }}</pre>
          </el-collapse-item>
        </el-collapse>
      </div>

      <div class="step7-view__body">
        <!-- Left: Agent Grid -->
        <div class="step7-view__main">
          <!-- No tasks yet -->
          <div v-if="taskStatesArray.length === 0" class="step7-view__empty-agents">
            <p>{{ streamStatus || '⏳ 等待后发解析TDD计划并创建子任务...' }}</p>
            <el-progress :percentage="100" :stroke-width="4" status="warning" indeterminate style="max-width:300px; margin:12px auto" />
          </div>

          <!-- Connected Agents Panel (always visible when agents are connected) -->
          <div v-if="connectedAgents.length > 0" class="step7-view__connected-agents">
            <h4>🐝 已连接Agent</h4>
            <div class="step7-view__agent-chips">
              <div v-for="a in connectedAgents" :key="a.name" class="step7-view__agent-chip" :class="'role-' + a.role">
                <span class="step7-view__agent-chip-icon">{{ a.role === 'writer' ? '✍️' : '🔍' }}</span>
                <span class="step7-view__agent-chip-name">{{ a.name }}</span>
                <el-tag size="small" :type="a.role === 'writer' ? 'warning' : 'primary'">{{ a.agentType }}</el-tag>
              </div>
            </div>
          </div>

          <div v-if="taskStatesArray.length > 0" class="step7-view__agents">
            <div
              v-for="task in taskStatesArray"
              :key="task.index"
              class="step7-view__agent-panel"
              :class="'status-' + task.status"
            >
              <div class="step7-view__agent-header">
                <span class="step7-view__agent-index">#{{ task.index }}</span>
                <span class="step7-view__agent-name">{{ task.name }}</span>
                <el-tag
                  :type="agentTagType[task.status]"
                  size="small"
                  effect="dark"
                >{{ agentStatusLabel[task.status] }}</el-tag>
              </div>

              <!-- Writer agent info -->
              <div class="step7-view__agent-body">
                <div class="step7-view__agent-line">
                  <span class="step7-view__agent-label">✍️ 编写Agent</span>
                  <span class="step7-view__agent-value">{{ task.writerAgent || '等待分配...' }}</span>
                  <el-button v-if="task.writerPrompt" text size="small" class="step7-view__prompt-toggle" @click="task.showWriterPrompt = !task.showWriterPrompt">
                    {{ task.showWriterPrompt ? '收起' : '提示词' }}
                  </el-button>
                </div>
                <div v-if="task.showWriterPrompt && task.writerPrompt" class="step7-view__prompt-box">
                  <pre>{{ task.writerPrompt }}</pre>
                </div>
                <div class="step7-view__agent-line">
                  <span class="step7-view__agent-label">🔍 测试Agent</span>
                  <span class="step7-view__agent-value">{{ task.testerAgent || '等待分配...' }}</span>
                  <el-button v-if="task.testerPrompt" text size="small" class="step7-view__prompt-toggle" @click="task.showTesterPrompt = !task.showTesterPrompt">
                    {{ task.showTesterPrompt ? '收起' : '提示词' }}
                  </el-button>
                </div>
                <div v-if="task.showTesterPrompt && task.testerPrompt" class="step7-view__prompt-box">
                  <pre>{{ task.testerPrompt }}</pre>
                </div>
                <div class="step7-view__agent-line" v-if="task.writerResponse || task.status === 'passed' || task.status === 'failed'">
                  <el-button v-if="task.writerResponse" text size="small" @click="task.showWriterResponse = !task.showWriterResponse">
                    {{ task.showWriterResponse ? '收起' : '📄 编写响应' }}
                  </el-button>
                  <span v-if="task.writerResponse && (task.status === 'passed' || task.status === 'failed')" class="step7-view__sep">|</span>
                  <el-button v-if="task.status === 'passed' || task.status === 'failed'" text size="small" type="primary" @click="openReport(task.testReportFull || task.testerResponse || '（报告为空）', `测试报告 - ${task.name}`)">
                    📄 检验报告
                  </el-button>
                </div>
                <div v-if="task.showWriterResponse && task.writerResponse" class="step7-view__response-box">
                  <pre>{{ task.writerResponse }}</pre>
                </div>
                <div class="step7-view__agent-line" v-if="task.testerResponse">
                  <el-button text size="small" @click="task.showTesterResponse = !task.showTesterResponse">
                    {{ task.showTesterResponse ? '收起' : '📄 测试响应' }}
                  </el-button>
                </div>
                <div v-if="task.showTesterResponse && task.testerResponse" class="step7-view__response-box">
                  <pre>{{ task.testerResponse }}</pre>
                </div>
                <div class="step7-view__agent-line" v-if="task.testerConclusion">
                  <span class="step7-view__agent-label">🔖 结论</span>
                  <span class="step7-view__agent-value" :class="task.testerConclusion === '检验通过' ? 'text-success' : 'text-danger'">{{ task.testerConclusion }}</span>
                </div>

                <div class="step7-view__agent-line" v-if="task.attempts > 0">
                  <span class="step7-view__agent-label">🔄 轮次</span>
                  <span class="step7-view__agent-value">{{ task.attempts }}/{{ MAX_ATTEMPTS }}</span>
                </div>              </div>
              <div v-if="task.message && !task.writerPrompt && !task.testerPrompt" class="step7-view__agent-msg">{{ task.message }}</div>
              <div class="step7-view__agent-bar">
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
        <div class="step7-view__sidebar">
          <div class="step7-view__sidebar-card">
            <h3>📋 TODO 清单</h3>
            <div class="step7-view__stats">
              <div class="step7-view__stat step7-view__stat--total">
                <span class="step7-view__stat-label">总计</span>
                <span class="step7-view__stat-value">{{ totalTasks }}</span>
              </div>
              <div class="step7-view__stat step7-view__stat--passed">
                <span class="step7-view__stat-label">✅ 通过</span>
                <span class="step7-view__stat-value">{{ passedCount }}</span>
              </div>
              <div class="step7-view__stat step7-view__stat--failed">
                <span class="step7-view__stat-label">❌ 失败</span>
                <span class="step7-view__stat-value">{{ failedCount }}</span>
              </div>
              <div class="step7-view__stat step7-view__stat--active">
                <span class="step7-view__stat-label">⏳ 进行中</span>
                <span class="step7-view__stat-value">{{ activeCount }}</span>
              </div>
              <div class="step7-view__stat step7-view__stat--pending">
                <span class="step7-view__stat-label">⏸️ 待执行</span>
                <span class="step7-view__stat-value">{{ pendingCount }}</span>
              </div>
            </div>
            <el-progress :percentage="progressPercent" :stroke-width="8" :color="progressColor" class="step7-view__progress-bar" />
            <div class="step7-view__task-list" ref="taskListRef">
              <div
                v-for="task in pendingTasksArray"
                :key="task.index"
                class="step7-view__task-item"
                :class="'status-' + task.status"
              >
                <span class="step7-view__task-icon">{{ taskIcon[task.status] }}</span>
                <span class="step7-view__task-name">{{ task.name }}</span>
                <span v-if="task.attempts > 0" class="step7-view__task-attempt">{{ task.attempts }}/{{ MAX_ATTEMPTS }}</span>
              </div>
              <div v-if="taskStatesArray.length === 0" class="step7-view__task-empty">{{ streamStatus || '暂无子任务' }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="step7-view__executing-actions">
        <div v-if="failedCount > 0" class="step7-view__resume-action" style="margin-bottom: 16px;">
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

      <el-collapse class="step7-view__stage-collapse">
        <el-collapse-item title="📋 完整执行日志" name="log">
          <div class="step7-view__stage-log">
            <div v-for="(msg, i) in stageLog" :key="i" class="step7-view__progress-msg" :class="msg.type">
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

    <!-- TDD cases preview -->
        <el-tabs v-model="activeDocTab">
          <el-tab-pane label="📄 TDD测试用例" name="cases">
            <div class="step7-view__doc-content" v-if="tddCases">
              <pre>{{ tddCases }}</pre>
            </div>
            <el-empty v-else description="暂无TDD用例内容" />
          </el-tab-pane>
          <el-tab-pane label="📊 执行统计" name="stats">
            <div class="step7-view__stats-detail" v-if="taskStatesArray.length">
              <div class="step7-view__stats-grid">
                <div class="step7-view__stats-item"><span>总测试用例</span><strong>{{ totalTasks }}</strong></div>
                <div class="step7-view__stats-item"><span>✅ 通过</span><strong class="text-success">{{ passedCount }}</strong></div>
                <div class="step7-view__stats-item"><span>❌ 失败</span><strong class="text-danger">{{ failedCount }}</strong></div>
                <div class="step7-view__stats-item"><span>🎲 抽检样本</span><strong>{{ spotCheckTotal }}</strong></div>
                <div class="step7-view__stats-item"><span>🎲 抽检不合格</span><strong class="text-danger">{{ spotCheckFailures }}</strong></div>
              </div>
            </div>
            <el-empty v-else description="暂无统计数据" />
          </el-tab-pane>
        </el-tabs>

      <div v-if="stepStatus === 'error'" class="step7-view__resume-section">
        <el-divider />
        <p class="step7-view__error-hint">{{ backendError || '部分子任务执行失败' }}</p>
        <div class="step7-view__actions">
          <el-button size="large" @click="goBack">返回项目</el-button>
          <el-button type="danger" size="large" :loading="executing" @click="handleExecute">🔄 强制重新执行</el-button>
        </div>
      </div>

      <div v-if="stepStatus === 'completed'" class="step7-view__complete-actions">
        <el-divider />
        <div class="step7-view__actions">
          <el-button size="large" @click="goBack">返回项目</el-button>
          <el-button type="primary" size="large" @click="goToNext">进入下一步 ➜</el-button>
        </div>
      </div>
  </div>

  <!-- 检验报告弹出对话框 -->
  <el-dialog v-model="reportDialogVisible" :title="reportDialogTitle" width="80%" top="5vh" :close-on-click-modal="true" destroy-on-close>
    <div class="step7-view__report-content">
      <pre>{{ reportDialogContent }}</pre>
    </div>
    <template #footer>
      <el-button @click="reportDialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
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
const tddCases = ref('')
const tddPlan = ref('')
const activeDocTab = ref('cases')
const spotCheckTotal = ref(0)
const spotCheckFailures = ref(0)

const reportDialogVisible = ref(false)
const reportDialogContent = ref('')
const reportDialogTitle = ref('')

function openReport(reportContent: string, title: string) {
  reportDialogContent.value = reportContent || '（报告为空）'
  reportDialogTitle.value = title
  reportDialogVisible.value = true
}

type TaskStatus = 'pending' | 'writing' | 'testing' | 'passed' | 'failed'

interface TaskState {
  index: number
  name: string
  writerAgent: string
  testerAgent: string
  status: TaskStatus
  attempts: number
  message: string
  writerPrompt: string
  testerPrompt: string
  showWriterPrompt: boolean
  showTesterPrompt: boolean
  writerResponse: string
  testerResponse: string
  showWriterResponse: boolean
  showTesterResponse: boolean
  testerConclusion: string
  testReportFull: string
  testReportFile: string
}

const taskStates = ref<Record<number, TaskState>>({})
const taskStatesArray = computed(() =>
  Object.values(taskStates.value).sort((a, b) => a.index - b.index)
)

const connectedAgents = ref<{name: string; role: string; agentType: string}[]>([])
const writerAgentsList = computed(() => connectedAgents.value.filter(a => a.role === 'writer'))
const testerAgentsList = computed(() => connectedAgents.value.filter(a => a.role === 'tester'))

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
  return `${base}/api/step7/progress/${props.projectId}?token=${encodeURIComponent(token)}`
}

function extractBracketName(msg: string): string | null {
  const m = msg.match(/\[([^\]]+)\]/)
  return m ? m[1] : null
}

function parseStep7Message(msg: { type: string; message?: string; content?: string; prompt?: string; agent?: string; subtask?: string; role?: string; response?: string; subtask_names?: string[] }) {
  // ── TDD计划内容 ──
  if (msg.type === 'tdd_plan' && msg.content) {
    tddPlan.value = msg.content
    if (msg.message) {
      streamStatus.value = msg.message
      stageLog.value.push({ type: 'progress', message: msg.message })
    }
    return
  }

  // ── Agent响应消息（无txt） ──
  if (msg.type === 'agent_response' && msg.subtask && msg.role) {
    const task = Object.values(taskStates.value).find(t => t.name === msg.subtask)
    if (task) {
      if (msg.role === 'writer') task.writerResponse = msg.response || ''
      else if (msg.role === 'tester') task.testerResponse = msg.response || ''
    }
    return
  }

  const txt = msg.message || ''
  if (!txt) return

  // Update the main status display with every broadcast
  streamStatus.value = txt

  // Also push to stage log
  stageLog.value.push({ type: 'progress', message: txt })

  // ── 解析TDD计划完成，预创建子任务 ──
  if (msg.subtask_names && Array.isArray(msg.subtask_names)) {
    for (const name of msg.subtask_names) {
      const existing = Object.values(taskStates.value).find(t => t.name === name)
      if (!existing) {
        const idx = Object.keys(taskStates.value).length + 1
        taskStates.value[idx] = {
          index: idx, name,
          writerAgent: '', testerAgent: '', status: 'pending',
          attempts: 0, message: '',
          writerPrompt: '', testerPrompt: '',
          showWriterPrompt: false, showTesterPrompt: false,
          writerResponse: '', testerResponse: '',
          showWriterResponse: false, showTesterResponse: false,
          testerConclusion: '',
          testReportFull: '', testReportFile: '',
        }
      }
    }
    return
  }

  // ── 提取子任务名 ──
  const sname = extractBracketName(txt)
  if (!sname) return

  // Find or create task by name
  let task = Object.values(taskStates.value).find(t => t.name === sname)
  if (!task) {
    // Create on first sight
    const idx = Object.keys(taskStates.value).length + 1
    task = { index: idx, name: sname, writerAgent: '', testerAgent: '', status: 'pending', attempts: 0, message: '', writerPrompt: '', testerPrompt: '', showWriterPrompt: false, showTesterPrompt: false, writerResponse: '', testerResponse: '', showWriterResponse: false, showTesterResponse: false, testerConclusion: '', testReportFull: '', testReportFile: '' }
    taskStates.value[idx] = task
  }

  task.message = txt

  // ── 提示词 ──
  if (msg.prompt && msg.agent) {
    // If writerAgent is already assigned and msg.agent is a different one → tester prompt
    if (task.writerAgent && task.writerAgent !== msg.agent) {
      task.testerAgent = msg.agent
      task.testerPrompt = msg.prompt
    } else {
      task.writerAgent = msg.agent
      task.writerPrompt = msg.prompt
    }
    return
  }

  // ── 正在编写 ──
  const writerMatch = txt.match(/✍️.*?编写（第(\d+)轮）/)
  if (writerMatch) {
    task.status = 'writing'
    task.attempts = parseInt(writerMatch[1])
    // Extract writer agent name: "✍️ [name] AgentName 编写..."
    const agentExtract = txt.match(/\] (.+?) 编写/)
    if (agentExtract) task.writerAgent = agentExtract[1].trim()
    scrollTaskList()
    return
  }

  // ── 正在验证 ──
  if (txt.includes('验证中')) {
    task.status = 'testing'
    const agentExtract = txt.match(/\] (.+?) 验证中/)
    if (agentExtract) task.testerAgent = agentExtract[1].trim()
    scrollTaskList()
    return
  }

  // ── 通过 ──
  // ── 补充提取检验报告 ──
  if (msg.test_report_full && msg.subtask) {
    const rtask = Object.values(taskStates.value).find(t => t.name === msg.subtask)
    if (rtask) {
      rtask.testReportFull = msg.test_report_full
      rtask.testReportFile = msg.test_report_file || ''
    }
  }

  const passMatch = txt.match(/✅.*?通过（第(\d+)轮）/)
  if (passMatch) {
    task.status = 'passed'
    task.attempts = parseInt(passMatch[1])
    if (msg.writerAgent) task.writerAgent = msg.writerAgent
    if (msg.testAgent) task.testerAgent = msg.testAgent
    scrollTaskList()
    return
  }

  // ── 未通过 ──
  if (txt.includes('⚠️') && txt.includes('未通过')) {
    task.status = 'writing'  // goes back to writing for next attempt
    return
  }

  // ── 5轮均未通过 ──
  if (txt.includes('❌') && txt.includes('均未通过')) {
    task.status = 'failed'
    if (msg.test_report_full) {
      task.testReportFull = msg.test_report_full
      task.testReportFile = msg.test_report_file || ''
    }
    const attemptMatch = txt.match(/(\d+)轮.*均未通过/)
    if (attemptMatch) task.attempts = parseInt(attemptMatch[1])
    scrollTaskList()
    return
  }

  // ── 统计汇总 ──
  const summaryMatch = txt.match(/子任务完成：(\d+)通过 /)
  if (summaryMatch) {
    streamStatus.value = txt
    return
  }

  // ── 蜂群就绪 ──
  if (txt.includes('蜂群就绪')) {
    streamStatus.value = txt
    return
  }

  // ── 抽检 ──
  const spotMatch = txt.match(/抽检(\d+)项不合格/)
  if (spotMatch) {
    spotCheckFailures.value = parseInt(spotMatch[1])
  }
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
        if (msg.type === 'step7' || msg.type === 'stage' || msg.type === 'progress') {
          if (msg.message) parseStep7Message(msg)
        } else if (msg.type === 'agent_online') {
          if (msg.name && !connectedAgents.value.find(a => a.name === msg.name)) {
            connectedAgents.value.push({name: msg.name, role: msg.role, agentType: msg.agent_type})
          }
        } else if (msg.type === 'agent_response') {
          parseStep7Message(msg)
        } else if (msg.type === 'content') {
          // handle content
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
              const step7Row = (res?.data || res)?.steps?.['7']
              if (step7Row?.status === 'completed') {
                router.push({ name: 'Step8', params: { projectId: props.projectId }, query: { name: projectName.value } })
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
      const s7 = data?.step7 || {}

      // Restore swarm summary if available
      if (s7.swarm_summary) {
        spotCheckTotal.value = s7.swarm_summary.spot_checked || 0
        spotCheckFailures.value = s7.swarm_summary.spot_failures || 0
      }

      // Restore subtask results
      if (s7.subtask_results) {
        for (const sr of s7.subtask_results) {
          const task = Object.values(taskStates.value).find(t => t.name === sr.name)
          if (task) {
            task.status = sr.status === 'passed' ? 'passed' : sr.status === 'failed' ? 'failed' : 'pending'
            task.attempts = sr.attempts || 0
            if (sr.writer) task.writerAgent = sr.writer
            if (sr.test_agent) task.testerAgent = sr.test_agent
            if (sr.tester_conclusion) task.testerConclusion = sr.tester_conclusion
            if (sr.test_report_full) task.testReportFull = sr.test_report_full
            if (sr.test_report_file) task.testReportFile = sr.test_report_file
          }
        }
      }

      if (s7.tdd_cases && s7.tdd_cases.trim().length > 50) {
        tddCases.value = s7.tdd_cases
      }

      const stepRow = data?.steps?.['7']
      if (stepRow?.status === 'completed') {
        stepStatus.value = 'completed'
        executing.value = false
        streamStatus.value = '✅ TDD测试用例已生成'
        clearAllTimers()
      } else if (stepRow?.status === 'qa_review') {
        stepStatus.value = 'qa_review'
        executing.value = false
        clearAllTimers()
      } else if (s7.status === 'error') {
        backendError.value = s7.message || '后端任务执行失败'
        streamStatus.value = '❌ 执行失败'
        stepStatus.value = 'error'
        clearAllTimers()
      } else if (data?.steps?.['7']?.status === 'in_progress') {
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
    const stepRow = steps['7'] || {}
    stepStatus.value = stepRow.status || 'pending'

    // 优先从专用步骤7状态 API 加载 artifacts（确保拿到最新数据）
    let s7 = data?.step7 || {}
    try {
      const artRes = await workflowApi.getStep7Status(props.projectId) as any
      if (artRes?.data && Object.keys(artRes.data).length > 0) {
        s7 = artRes.data
      }
    } catch {}

    if (s7.tdd_cases && s7.tdd_cases.trim().length > 50) {
      tddCases.value = s7.tdd_cases
    }
    if (s7.swarm_summary) {
      spotCheckTotal.value = s7.swarm_summary.spot_checked || 0
      spotCheckFailures.value = s7.swarm_summary.spot_failures || 0
    }

    // ── 强制定位每个子任务状态 ──
    if (s7.subtask_results) {
      for (const sr of s7.subtask_results) {
        const existing = Object.values(taskStates.value).find(t => t.name === sr.name)
        const resolvedStatus: string = sr.status === 'passed' ? 'passed' : sr.status === 'failed' ? 'failed' : 'pending'
        if (existing) {
          existing.status = resolvedStatus
          existing.attempts = sr.attempts || 0
          if (sr.writer) existing.writerAgent = sr.writer
          if (sr.test_agent) existing.testerAgent = sr.test_agent
          if (sr.tester_conclusion) existing.testerConclusion = sr.tester_conclusion
          if (sr.test_report_full) existing.testReportFull = sr.test_report_full
          if (sr.test_report_file) existing.testReportFile = sr.test_report_file
        } else {
          const idx = Object.keys(taskStates.value).length + 1
          taskStates.value[idx] = {
            index: idx, name: sr.name,
            writerAgent: sr.writer || '', testerAgent: sr.test_agent || '',
            status: resolvedStatus,
            attempts: sr.attempts || 0, message: '', writerPrompt: '', testerPrompt: '', showWriterPrompt: false, showTesterPrompt: false,
            writerResponse: '', testerResponse: '', showWriterResponse: false, showTesterResponse: false,
            testerConclusion: '',
            testReportFull: sr.test_report_full || '', testReportFile: sr.test_report_file || '',
          }
        }
      }
    }

    if (s7.message) {
      stageLog.value.push({ type: 'stage', message: s7.message })
    }

    if (stepStatus.value === 'pending') {
      // 有已保存的子任务结果 → 从 DB 恢复
      if (s7.subtask_results && s7.subtask_results.length > 0) {
        const allPassed = s7.subtask_results.every(sr => sr.status === 'passed')
        if (allPassed) {
          stageLog.value.push({ type: 'stage', message: `♻️ 从数据库恢复 ${s7.subtask_results.length} 个子任务状态` })
          streamStatus.value = '✅ 所有子任务已通过'
          stepStatus.value = 'completed'
          stageLog.value.push({ type: 'stage', message: '✅ 所有子任务均已通过检验' })
        } else {
          // 有部分已通过 + 部分失败/待执行 → 自动续跑未通过子任务
          const passedCount = s7.subtask_results.filter(sr => sr.status === 'passed').length
          const pendingCount = s7.subtask_results.length - passedCount
          stageLog.value.push({ type: 'stage', message: `♻️ 恢复 ${passedCount} 个已通过 + ${pendingCount} 个待重置子任务，自动启动续跑...` })
          streamStatus.value = `♻️ 自动续跑 ${pendingCount} 个未通过子任务...`
          setTimeout(() => handleExecute(), 500)
        }
      } else {
        stageLog.value.push({ type: 'stage', message: '🚀 准备启动后发蜂群并行编写TDD测试用例...' })
        setTimeout(() => handleExecute(), 300)
      }
    }

    if (stepStatus.value === 'in_progress') {
      // 如果所有子任务均已通过，直接切换到 completed
      if (s7.subtask_results && s7.subtask_results.length > 0 && s7.subtask_results.every(sr => sr.status === 'passed')) {
        stepStatus.value = 'completed'
        streamStatus.value = '✅ 所有子任务已通过'
        stageLog.value.push({ type: 'stage', message: '✅ 所有子任务均已通过检验' })
        clearAllTimers()
      } else {
        connectWs()
        startPolling()
        resetStuckTimer()
        const hasRealData = !!(s7.tdd_cases || s7.subtask_results || s7.swarm_summary)
        const hasFailedOrPending = s7.subtask_results && s7.subtask_results.some(sr => sr.status === 'failed' || sr.status === 'pending')
        if (!hasRealData) {
          stageLog.value.push({ type: 'stage', message: '🚀 检测到步骤7已就绪但未启动，正在自动触发执行...' })
          setTimeout(() => handleExecute(), 500)
        } else if (hasFailedOrPending) {
          stageLog.value.push({ type: 'stage', message: '🔄 检测到有未通过的子任务，正在自动续跑...' })
          setTimeout(() => handleExecute(), 500)
        }
      }
    }

    if (stepStatus.value === 'completed' && !tddCases.value) {
      loading.value = true
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
  tddCases.value = ''
  stageLog.value = [{ type: 'stage', message: '🐝 正在启动后发蜂群...' }]
  streamStatus.value = '🐝 正在启动后发蜂群...'
  stepStatus.value = 'in_progress'
  connectedAgents.value = []
  spotCheckTotal.value = 0
  spotCheckFailures.value = 0
  clearAllTimers()

  connectWs()
  await waitForWs()
  startPolling()
  resetStuckTimer()

  try {
    const res = await workflowApi.executeStep(props.projectId, 7) as any
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
  stageLog.value = [{ type: 'stage', message: '♻️ 强制重新执行 step7...' }]
  taskStates.value = {}
  connectedAgents.value = []
  connectWs()
  await waitForWs()
  startPolling()
  resetStuckTimer()
  try {
    await workflowApi.executeStep(props.projectId, 7)
  } catch (e: any) {
    error.value = e?.message || '重试失败'
  } finally {
    restarting.value = false
  }
}

function goBack() { router.push({ name: 'ProjectDetail', params: { projectId: props.projectId } }) }
function goToNext() { router.push({ name: 'Step8', params: { projectId: props.projectId }, query: { name: projectName.value } }) }

onMounted(() => loadStatus())
onUnmounted(() => {
  clearAllTimers()
  if (ws) { ws.onclose = null; ws.close(); ws = null }
})
</script>

<style scoped lang="scss">
.step7-view {
  max-width: 1200px; margin: 0 auto; padding: 32px 24px;

  &__header {
    display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px;
    &-left { display: flex; align-items: flex-start; gap: 16px; h1 { margin: 0; font-size: 24px; font-weight: 600; } }
  }
  &__subtitle { margin: 4px 0 0; color: #909399; font-size: 14px; }
  &__alert { margin-bottom: 16px; }

  &__card {
    text-align: center; padding: 32px 24px; background: #fff; border: 1px solid #e4e7ed; border-radius: 8px;
    h2 { margin: 16px 0 8px; font-size: 20px; font-weight: 600; }
    p { color: #909399; margin: 0 0 24px; }
    &-icon { font-size: 48px; line-height: 1; }
  }

  // ── loading: 自动启动 ──
  &__loading-start {
    text-align: center; padding: 60px 24px; background: #fff; border: 1px solid #e4e7ed; border-radius: 8px;
    h2 { margin: 16px 0 8px; font-size: 20px; font-weight: 600; }
    p { color: #909399; margin: 0 0 12px; }
    &-icon { font-size: 48px; line-height: 1; }
  }

  // ── executing ──
  &__executing {
    background: #fff; border: 1px solid #e4e7ed; border-radius: 8px; padding: 20px;
    &-header { display: flex; align-items: center; gap: 16px; margin-bottom: 16px;
      .step7-view__card-icon { font-size: 36px; }
      h2 { margin: 0; font-size: 18px; font-weight: 600; }
    }
    &-status { font-size: 14px; color: #e6a23c; font-weight: 500; margin: 4px 0 0 !important; }
  }

  &__tdd-plan {
    margin-bottom: 16px;
    .el-collapse { border-radius: 8px; border: 1px solid #e4e7ed; }
    &-content {
      font-size: 13px; line-height: 1.6; max-height: 400px; overflow-y: auto;
      white-space: pre-wrap; word-break: break-all; background: #fafafa;
      padding: 12px; border-radius: 4px; margin: 0;
    }
  }

  &__body {
    display: flex; gap: 16px; align-items: flex-start;
  }

  // ── Left: agent grid ──
  &__main { flex: 1; min-width: 0; }

  &__empty-agents {
    text-align: center; padding: 40px 20px; color: #909399;
    p { font-size: 15px; margin: 0; }
  }

  &__connected-agents {
    margin-bottom: 12px; padding: 10px 12px; background: #f5f7fa; border-radius: 8px;
    h4 { margin: 0 0 8px; font-size: 14px; font-weight: 600; }
  }
  &__agent-chips { display: flex; flex-wrap: wrap; gap: 6px; }
  &__agent-chip {
    display: flex; align-items: center; gap: 4px; padding: 4px 10px;
    border-radius: 16px; font-size: 12px; border: 1px solid #e4e7ed; background: #fff;
    &.role-writer { border-color: #e6a23c; background: #fffbe6; }
    &.role-tester { border-color: #409eff; background: #ecf5ff; }
    &-icon { font-size: 14px; }
    &-name { font-weight: 500; }
  }

  &__agents {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 10px;
  }

  &__agent-panel {
    background: #fff; border: 1px solid #e4e7ed; border-radius: 8px; padding: 10px 12px;
    transition: all 0.3s ease;
    &.status-writing { border-color: #e6a23c; background: #fffbe6; }
    &.status-testing { border-color: #409eff; background: #ecf5ff; }
    &.status-passed { border-color: #67c23a; background: #f0f9eb; }
    &.status-failed { border-color: #f56c6c; background: #fef0f0; }
    &.status-pending { border-color: #dcdfe6; background: #fafafa; }
  }

  &__agent-header {
    display: flex; align-items: center; gap: 6px; margin-bottom: 6px;
  }
  &__agent-index { font-size: 11px; color: #909399; background: #f5f7fa; padding: 1px 5px; border-radius: 3px; min-width: 22px; text-align: center; }
  &__agent-name { font-weight: 600; font-size: 13px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  &__agent-body { margin-bottom: 4px; }
  &__agent-line { display: flex; align-items: center; gap: 4px; font-size: 12px; margin-bottom: 2px; }
  &__agent-label { color: #909399; min-width: 48px; font-size: 11px; }
  &__agent-value { color: #303133; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  &__agent-msg { font-size: 11px; color: #606266; line-height: 1.3; margin-bottom: 4px; }
  &__agent-bar { margin-top: 4px; }

  // ── Right: TODO sidebar ──
  &__sidebar { width: 280px; flex-shrink: 0; }
  &__sidebar-card {
    background: #fff; border: 1px solid #e4e7ed; border-radius: 8px; padding: 16px;
    position: sticky; top: 16px;
    h3 { margin: 0 0 12px; font-size: 16px; font-weight: 600; }
  }

  &__stats { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 12px; }
  &__stat {
    padding: 8px 10px; border-radius: 6px; border: 1px solid #ebeef5;
    display: flex; justify-content: space-between; align-items: center;
    font-size: 13px;
    &--total { background: #f5f7fa; grid-column: 1 / -1; }
    &--passed { background: #f0f9eb; border-color: #b3e19d; }
    &--failed { background: #fef0f0; border-color: #fbc4c4; }
    &--active { background: #ecf5ff; border-color: #a6c8ff; }
    &--pending { background: #fafafa; border-color: #dcdfe6; }
    &-value { font-weight: 700; font-size: 16px; }
  }

  &__progress-bar { margin-bottom: 12px; }

  &__task-list { max-height: 400px; overflow-y: auto; }
  &__task-item {
    display: flex; align-items: center; gap: 6px; padding: 6px 8px;
    border-radius: 4px; font-size: 12px; margin-bottom: 3px;
    border-left: 3px solid transparent;
    &.status-passed { background: #f0f9eb; border-color: #67c23a; }
    &.status-failed { background: #fef0f0; border-color: #f56c6c; }
    &.status-writing, &.status-testing { background: #fdf6ec; border-color: #e6a23c; }
    &.status-pending { border-color: #dcdfe6; }
  }
  &__task-icon { font-size: 14px; }
  &__task-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  &__task-attempt { font-size: 10px; color: #909399; }
  &__task-empty { text-align: center; color: #c0c4cc; padding: 20px 0; font-size: 13px; }

  &__prompt-toggle { font-size: 11px; color: #409eff; padding: 0 4px; }
  &__sep { color: #dcdfe6; font-size: 12px; margin: 0 2px; }
  &__prompt-box {
    grid-column: 1 / -1; margin: 4px 0 8px 0;
    pre {
      background: #f5f7fa; border: 1px solid #e4e7ed; border-radius: 4px;
      padding: 8px; font-size: 11px; line-height: 1.4; max-height: 200px;
      overflow-y: auto; white-space: pre-wrap; word-break: break-all; margin: 0;
    }
  }
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
    line-height: 1.4; background: #fff; border: 1px solid #ebeef5;
    &.stage { border-left: 3px solid #e6a23c; }
    &.done { border-left: 3px solid #67c23a; background: #f0f9eb; }
    &.error { border-left: 3px solid #f56c6c; background: #fef0f0; }
  }

  // ── result panel (qa_review / completed / error) ──
  &__result { margin-top: 16px; }

  &__summary {
    display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;
  }
  &__summary-card {
    display: flex; align-items: center; gap: 8px; padding: 8px 12px;
    border-radius: 8px; border: 1px solid #e4e7ed; background: #fff;
    flex: 1; min-width: 160px;
    &.status-passed { border-color: #67c23a; background: #f0f9eb; }
    &.status-failed { border-color: #f56c6c; background: #fef0f0; }
  }
  &__summary-icon { font-size: 20px; }
  &__summary-body { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  &__summary-label { font-weight: 500; font-size: 13px; }
  &__summary-rounds { font-size: 11px; color: #909399; }

  &__resume-action { margin-top: 8px; width: 100%; text-align: center; }

  &__tabs { background: #fff; border: 1px solid #e4e7ed; border-radius: 8px; padding: 16px; margin-top: 12px; }
  &__doc-content { max-height: 600px; overflow-y: auto;
    pre { white-space: pre-wrap; word-break: break-word; font-size: 13px; line-height: 1.6; margin: 0; }
  }
  &__stats-detail { padding: 8px 0; }
  &__stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  &__stats-item {
    padding: 12px 16px; background: #f5f7fa; border-radius: 6px;
    display: flex; justify-content: space-between; align-items: center;
    font-size: 14px;
    strong { font-size: 18px; }
  }

  &__resume-section { margin-top: 24px; }
  &__error-hint { text-align: center; color: #f56c6c; font-size: 14px; margin: 0 0 16px; }
  &__complete-actions { margin-top: 24px; }
  &__actions { display: flex; justify-content: center; gap: 12px; }
}

.text-success { color: #67c23a; }
.text-danger { color: #f56c6c; }

.step7-view__report-content {
  max-height: 70vh;
  overflow-y: auto;
  pre {
    white-space: pre-wrap;
    word-break: break-all;
    font-size: 13px;
    line-height: 1.6;
    margin: 0;
  }
}
</style>
