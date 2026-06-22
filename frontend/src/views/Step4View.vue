<template>
  <div class="step4-view" v-loading="loading">
    <div class="step4-view__header">
      <div class="step4-view__header-left">
        <el-button :icon="ArrowLeft" text @click="goBack">返回</el-button>
        <div>
          <h1>第四步：架构设计</h1>
          <p class="step4-view__subtitle">{{ projectName }} · 4个子流程并行</p>
        </div>
      </div>
      <div class="step4-view__header-right">
        <el-tag :type="statusTag" effect="dark" size="large">{{ statusLabel }}</el-tag>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon closable class="step4-view__alert" />

    <!-- idle -->
    <div v-if="stepStatus === 'idle'" class="step4-view__card">
      <div class="step4-view__card-icon">🏗️</div>
      <h2>准备执行架构设计（4子流程并行）</h2>
      <p>后旺1~4号将根据需求文档并行生成以下设计文档，后荣1~4号同步检验：</p>
      <div class="step4-view__doc-list-preview">
        <div class="step4-view__doc-type-item"><span class="step4-view__doc-type-icon">🏛️</span><div><div class="step4-view__doc-type-name">架构设计文档</div><div class="step4-view__doc-type-desc">系统整体架构、分层、模块划分、技术栈</div></div></div>
        <div class="step4-view__doc-type-item"><span class="step4-view__doc-type-icon">🎨</span><div><div class="step4-view__doc-type-name">前端设计文档</div><div class="step4-view__doc-type-desc">前端技术栈、组件树、路由、状态管理</div></div></div>
        <div class="step4-view__doc-type-item"><span class="step4-view__doc-type-icon">⚙️</span><div><div class="step4-view__doc-type-name">后端设计文档</div><div class="step4-view__doc-type-desc">后端技术栈、API接口、数据流、安全策略</div></div></div>
        <div class="step4-view__doc-type-item"><span class="step4-view__doc-type-icon">🗄️</span><div><div class="step4-view__doc-type-name">数据库设计脚本</div><div class="step4-view__doc-type-desc">完整 SQL DDL、表结构、索引、外键</div></div></div>
      </div>
      <el-button type="primary" size="large" :loading="executing" @click="handleExecute">
        {{ executing ? '后旺执行中...' : '开始执行' }}
      </el-button>
    </div>

    <!-- executing: 4 parallel sub-flow panels -->
    <div v-if="stepStatus === 'executing'" class="step4-view__card step4-view__card--executing">
      <div class="step4-view__executing-header">
        <div class="step4-view__card-icon">🏗️</div>
        <h2>4个子流程并行运行</h2>
      </div>
      <p class="step4-view__executing-status">{{ streamStatus }}</p>

      <el-alert
        v-if="stuckWarning"
        :title="stuckWarning"
        type="warning"
        show-icon
        closable
        class="step4-view__alert"
      />
      <el-alert
        v-if="backendError"
        :title="backendError"
        type="error"
        show-icon
        closable
        class="step4-view__alert"
        @close="backendError = ''"
      />

      <div class="step4-view__subflows">
        <div
          v-for="sf in subFlowStatesArray"
          :key="sf.key"
          class="step4-view__subflow-panel"
          :class="'status-' + sf.status"
        >
          <div class="step4-view__subflow-header">
            <span class="step4-view__subflow-icon">{{ sf.icon }}</span>
            <span class="step4-view__subflow-label">{{ sf.label }}</span>
            <el-tag :type="({pending:'info',generating:'warning',reviewing:'primary',passed:'success',failed:'danger'} as Record<string,string>)[sf.status] || 'info'" size="small" effect="dark">{{ ({pending:'待执行',generating:'生成中',reviewing:'检验中',passed:'✅通过',failed:'❌未通过'} as Record<string,string>)[sf.status] || sf.status }}</el-tag>
            <span v-if="sf.rounds > 0" class="step4-view__subflow-rounds">第{{ sf.rounds }}轮</span>
          </div>
          <div v-if="sf.message" class="step4-view__subflow-message">{{ sf.message }}</div>
          <div v-if="sf.detail" class="step4-view__subflow-detail">{{ sf.detail }}</div>
          <div v-if="sf.content.trim()" class="step4-view__subflow-content">
            <pre>{{ sf.content }}</pre>
          </div>
          <div v-if="sf.status === 'generating' || sf.status === 'reviewing'" class="step4-view__subflow-bar">
            <el-progress :percentage="100" :stroke-width="4" status="warning" indeterminate />
          </div>
        </div>
      </div>

      <div class="step4-view__executing-actions">
        <el-button
          v-if="stuckWarning || backendError"
          type="danger"
          size="large"
          :loading="restarting"
          @click="handleRestart"
        >
          🔄 强制重新执行
        </el-button>
        <el-button
          type="warning"
          plain
          size="large"
          :loading="restarting"
          @click="handleRestart"
        >
          🛑 停止并重新开始
        </el-button>
      </div>

      <el-collapse class="step4-view__stage-collapse">
        <el-collapse-item title="📋 完整执行日志" name="log">
          <div class="step4-view__stage-log">
            <div v-for="(msg, i) in stageLog" :key="i" class="step4-view__progress-msg" :class="msg.type">
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

    <!-- qa_review / qa_passed -->
    <div v-if="stepStatus === 'qa_review' || stepStatus === 'qa_passed'" class="step4-view__result">
      <!-- sub-flow summary cards (always show for tracking) -->
      <div v-if="subFlowSummary.length" class="step4-view__summary">
        <div
          v-for="sf in subFlowSummary"
          :key="sf.key"
          class="step4-view__summary-card"
          :class="'status-' + sf.status"
        >
          <span class="step4-view__summary-icon">{{ sf.icon }}</span>
          <div class="step4-view__summary-body">
            <div class="step4-view__summary-label">{{ sf.label }}</div>
            <el-tag :type="sf.status === 'passed' ? 'success' : sf.status === 'failed' ? 'danger' : 'info'" size="small">
              {{ sf.status === 'passed' ? '✅ 通过' : sf.status === 'failed' ? '❌ 未通过' : '⏳ 未执行' }}
            </el-tag>
            <span v-if="sf.rounds > 0" class="step4-view__summary-rounds">{{ sf.rounds }}轮</span>
          </div>
        </div>

        <!-- Resume button: only run failed/pending sub-flows, never re-run passed ones -->
        <div v-if="subFlowSummary.some(s => s.status !== 'passed')" class="step4-view__resume-action">
          <el-button
            type="primary"
            size="large"
            :loading="executing"
            @click="handleResumeFailed"
          >
            {{ executing ? '执行中...' : `🔄 续跑未完成项（跳过已通过的${subFlowSummary.filter(s => s.status === 'passed').length}项，运行${subFlowSummary.filter(s => s.status !== 'passed').length}项）` }}
          </el-button>
        </div>
      </div>

      <div class="step4-view__tabs">
        <el-tabs v-model="activeDocTab">
          <el-tab-pane label="架构设计" name="architecture"><div class="step4-view__doc-content" v-if="parsedDocs.architecture"><pre>{{ parsedDocs.architecture }}</pre></div><el-empty v-else description="暂无架构设计内容" /></el-tab-pane>
          <el-tab-pane label="前端设计" name="frontend"><div class="step4-view__doc-content" v-if="parsedDocs.frontend"><pre>{{ parsedDocs.frontend }}</pre></div><el-empty v-else description="暂无前端设计内容" /></el-tab-pane>
          <el-tab-pane label="后端设计" name="backend"><div class="step4-view__doc-content" v-if="parsedDocs.backend"><pre>{{ parsedDocs.backend }}</pre></div><el-empty v-else description="暂无后端设计内容" /></el-tab-pane>
          <el-tab-pane label="数据库设计" name="database"><div class="step4-view__doc-content" v-if="parsedDocs.database"><pre>{{ parsedDocs.database }}</pre></div><el-empty v-else description="暂无数据库设计内容" /></el-tab-pane>
          <el-tab-pane label="全部" name="all"><div class="step4-view__doc-content" v-if="designDoc"><pre>{{ designDoc }}</pre></div><el-empty v-else description="暂无设计文档" /></el-tab-pane>
        </el-tabs>
      </div>

      <div v-if="stepStatus === 'qa_review'" class="step4-view__qa-section">
        <el-divider />
        <h3>🔍 后荣 QA 检验</h3>
        <p class="step4-view__qa-subtitle">检验架构设计方案是否达到验收标准</p>
        <div v-if="qaLoading" class="step4-view__qa-loading"><el-progress :percentage="qaProgress" :stroke-width="6" status="warning" /><p>后荣正在检验设计方案...</p></div>
        <div v-else-if="qaChecked" class="step4-view__qa-result">
          <div v-for="dim in qaDimensions" :key="dim.key" class="step4-view__qa-dimension">
            <div class="step4-view__qa-dimension-header"><el-tag :type="dim.passed ? 'success' : 'danger'" size="small" effect="dark">{{ dim.passed ? '✅ 通过' : '❌ 不通过' }}</el-tag><span class="step4-view__qa-dimension-label">{{ dim.label }}</span></div>
            <p class="step4-view__qa-dimension-detail">{{ dim.detail }}</p>
          </div>
          <div v-if="qaPassed" class="step4-view__qa-actions"><el-button type="primary" size="large" @click="handleComplete">✅ QA通过，进入下一步 ➜</el-button></div>
          <div v-else class="step4-view__qa-actions"><el-button type="primary" size="large" @click="handleRunQA">重新检验</el-button></div>
        </div>
        <div v-else class="step4-view__qa-start"><el-button type="primary" size="large" :loading="qaLoading" @click="handleRunQA">开始 QA 检验</el-button></div>
      </div>

      <div v-if="stepStatus === 'qa_passed'" class="step4-view__complete-actions">
        <el-divider />
        <div class="step4-view__actions"><el-button size="large" @click="goBack">返回项目</el-button><el-button type="primary" size="large" @click="goToNext">进入下一步 ➜</el-button></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { workflowApi } from '@/api/modules/workflow'

const props = defineProps<{ projectId: string }>()
const router = useRouter()
const route = useRoute()
const projectName = (route.query.name as string) || '未命名项目'

const loading = ref(false)
const executing = ref(false)
const error = ref('')
const stepStatus = ref<'idle' | 'executing' | 'qa_review' | 'qa_passed'>('idle')
const designDoc = ref('')
const activeDocTab = ref('architecture')
const streamStatus = ref('')
const stageLog = ref<{ type: string; message: string; subflow?: string }[]>([])
const liveContent = ref('')

// QA state
const qaLoading = ref(false)
const qaProgress = ref(0)
const qaChecked = ref(false)
const qaPassed = ref(false)
const qaDimensions = ref<{ key: string; label: string; description: string; passed: boolean; detail: string }[]>([])
const hasExistingResults = ref(false)

// Restart / stuck recovery
const restarting = ref(false)
const stuckWarning = ref('')
const backendError = ref('')
let wsTimer: ReturnType<typeof setTimeout> | null = null
const STUCK_TIMEOUT_MS = 120000  // 2分钟无WS消息视为卡死

type SubFlowStatus = 'pending' | 'generating' | 'reviewing' | 'passed' | 'failed'

interface SubFlowState {
  key: string
  label: string
  icon: string
  status: SubFlowStatus
  message: string
  content: string
  rounds: number
  detail: string
}

const defaultSubFlows: Record<string, SubFlowState> = {
  arch_reasonableness: { key: 'arch_reasonableness', label: '架构设计', icon: '🏛️', status: 'pending', message: '等待执行', content: '', rounds: 0, detail: '' },
  frontend_feasibility: { key: 'frontend_feasibility', label: '前端设计', icon: '🎨', status: 'pending', message: '等待执行', content: '', rounds: 0, detail: '' },
  backend_feasibility: { key: 'backend_feasibility', label: '后端设计', icon: '⚙️', status: 'pending', message: '等待执行', content: '', rounds: 0, detail: '' },
  database_design: { key: 'database_design', label: '数据库设计', icon: '🗄️', status: 'pending', message: '等待执行', content: '', rounds: 0, detail: '' },
}

const subFlowStates = ref<Record<string, SubFlowState>>(JSON.parse(JSON.stringify(defaultSubFlows)))

function resetSubFlowStates() {
  subFlowStates.value = JSON.parse(JSON.stringify(defaultSubFlows))
}

const subFlowStatesArray = computed(() => Object.values(subFlowStates.value))

const subFlowMap: Record<string, string> = {
  'ARCHITECTURE': 'arch_reasonableness',
  'FRONTEND': 'frontend_feasibility',
  'BACKEND': 'backend_feasibility',
  'DATABASE': 'database_design',
}

const subFlowLabelMap: Record<string, string> = {
  '架构': 'arch_reasonableness',
  '前端': 'frontend_feasibility',
  '后端': 'backend_feasibility',
  '数据库': 'database_design',
}

function inferSubflow(msg: string): string | null {
  for (const [kw, key] of Object.entries(subFlowLabelMap)) {
    if (msg.includes(kw)) return key
  }
  return null
}

function updateSubFlowState(key: string, patch: Partial<SubFlowState>) {
  if (subFlowStates.value[key]) {
    Object.assign(subFlowStates.value[key], patch)
  }
}

function parseSubFlowMessage(msg: { type: string; message?: string; content?: string; subflow?: string }) {
  const sfKey = msg.subflow || (msg.message ? inferSubflow(msg.message) : null)
  if (!sfKey || !subFlowStates.value[sfKey]) {
    if (msg.message) stageLog.value.push({ type: msg.type, message: msg.message, subflow: msg.subflow })
    return
  }
  if (msg.message) stageLog.value.push({ type: msg.type, message: msg.message, subflow: sfKey })

  if (msg.type === 'stage' || msg.type === 'progress') {
    const txt = msg.message || ''

    // ── passed: 优先匹配通过类关键词 ──
    if (txt.includes('检验通过') || txt.includes('已通过 hourong 检验')) {
      updateSubFlowState(sfKey, { status: 'passed', message: txt })
      const roundMatch = txt.match(/(\d+)轮/)
      if (roundMatch) updateSubFlowState(sfKey, { rounds: parseInt(roundMatch[1]) })

    // ── failed: 再匹配未通过类关键词 ──
    } else if (txt.includes('检验未通过') || txt.includes('未通过')) {
      updateSubFlowState(sfKey, { status: 'failed', message: txt })
      const roundMatch = txt.match(/第(\d+)轮/)
      if (roundMatch) updateSubFlowState(sfKey, { rounds: parseInt(roundMatch[1]) })

    // ── generating: 正在生成/修复/更新 ──
    } else if (
      txt.includes('正在生成') || txt.includes('正在从需求生成') ||
      txt.includes('正在根据') || txt.includes('修复') || txt.includes('更新')
    ) {
      updateSubFlowState(sfKey, { status: 'generating', message: txt })

    // ── reviewing: 正在检验 ──
    } else if (txt.includes('正在检验') || txt.includes('提交至 hourong 检验')) {
      updateSubFlowState(sfKey, { status: 'reviewing', message: txt })

    } else {
      updateSubFlowState(sfKey, { message: txt })
    }

    const detailMatch = txt.match(/意见[：:](.+)$|意见[：:]\s*(.+)/)
    if (detailMatch) {
      updateSubFlowState(sfKey, { detail: detailMatch[1] || detailMatch[2] || '' })
    }
  } else if (msg.type === 'content') {
    const c = msg.content || ''
    subFlowStates.value[sfKey].content += c
  }
}

interface SubFlowSummary {
  key: string
  label: string
  icon: string
  status: SubFlowStatus
  rounds: number
  message?: string
}

const subFlowSummary = computed<SubFlowSummary[]>(() => {
  const result: SubFlowSummary[] = []
  for (const sf of Object.values(subFlowStates.value)) {
    if (sf.status === 'passed' || sf.status === 'failed' || sf.status === 'pending') {
      result.push({ key: sf.key, label: sf.label, icon: sf.icon, status: sf.status, rounds: sf.rounds, message: sf.message })
    }
  }
  return result
})

interface ParsedDocs {
  architecture: string
  frontend: string
  backend: string
  database: string
}

const parsedDocs = computed<ParsedDocs>(() => {
  const result: ParsedDocs = { architecture: '', frontend: '', backend: '', database: '' }
  const doc = designDoc.value
  if (!doc) return result
  const sections = doc.split(/(?=^# )/m)
  for (const section of sections) {
    const trimmed = section.trim()
    if (!trimmed) continue
    const header = trimmed.split('\n')[0].replace('# ', '').trim()
    if (header.includes('架构') || header.includes('Architecture')) result.architecture = trimmed
    else if (header.includes('前端') || header.includes('Frontend')) result.frontend = trimmed
    else if (header.includes('后端') || header.includes('Backend')) result.backend = trimmed
    else if (header.includes('数据库') || header.includes('Database') || header.includes('SQL') || header.includes('DDL')) result.database = trimmed
  }
  return result
})

const statusTag = computed(() => {
  const map: Record<string, string> = { idle: 'info', executing: 'warning', qa_review: 'warning', qa_passed: 'success' }
  return map[stepStatus.value] || 'info'
})

const statusLabel = computed(() => {
  const map: Record<string, string> = { idle: '待执行', executing: '生成中...', qa_review: '待检验', qa_passed: '已完成' }
  return map[stepStatus.value] || stepStatus.value
})

function getProgressWsUrl(): string {
  const token = localStorage.getItem('access_token') || ''
  const port = import.meta.env.VITE_BACKEND_PORT || '9000'
  const base = import.meta.env.VITE_WS_BASE_URL || `ws://${location.hostname}:${port}`
  return `${base}/api/step4/progress/${props.projectId}?token=${encodeURIComponent(token)}`
}

let ws: WebSocket | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null

function resetStuckTimer() {
  if (wsTimer) { clearTimeout(wsTimer); wsTimer = null }
  wsTimer = setTimeout(() => {
    if (stepStatus.value === 'executing') {
      stuckWarning.value = '⚠️ 长时间未收到后旺/后荣的实时消息，可能已中断。请点"强制重新执行"恢复。'
    }
  }, STUCK_TIMEOUT_MS)
}

function clearAllTimers() {
  if (wsTimer) { clearTimeout(wsTimer); wsTimer = null }
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

function connectProgressWs() {
  if (ws) { ws.onclose = null; ws.close(); ws = null }
  try {
    ws = new WebSocket(getProgressWsUrl())
    ws.onmessage = (event) => {
      try {
        resetStuckTimer()
        stuckWarning.value = ''
        const msg = JSON.parse(event.data)
        if (msg.type === 'error') {
          backendError.value = msg.message || '后端执行出错'
        }
        if (msg.subflow) {
          parseSubFlowMessage(msg)
        } else {
          if (msg.type === 'stage' || msg.type === 'progress') {
            if (msg.message) stageLog.value.push({ type: msg.type, message: msg.message })
          } else if (msg.type === 'content') {
            liveContent.value += msg.content
          } else if (msg.type === 'done') {
            if (msg.message) stageLog.value.push({ type: 'done', message: msg.message })
            streamStatus.value = '✅ 4子流程执行完成'
          } else if (msg.type === 'error') {
            if (msg.message) stageLog.value.push({ type: 'error', message: msg.message })
          }
        }
        if (msg.type === 'done' || msg.type === 'error') {
          streamStatus.value = msg.message || streamStatus.value
        }
      } catch { /* ignore parse errors */ }
    }
    ws.onclose = () => { ws = null }
    ws.onerror = () => { ws = null }
  } catch { /* fall back to polling */ }
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await workflowApi.getStatus(props.projectId) as any
    const data = res?.data || res
    const s4 = data?.step4 || {}
    if (s4.design_doc) designDoc.value = s4.design_doc
    // 无论步骤状态如何，先恢复已保存的子流程结果
    if (s4.sub_flow_results) {
      for (const sr of s4.sub_flow_results) {
        const sf = subFlowStates.value[sr.key]
        if (sf) {
          sf.status = sr.passed ? 'passed' : 'failed'
          sf.rounds = sr.rounds || 0
          sf.detail = sr.convergence?.length ? '' : ''
        }
      }
    }

    if (data?.steps?.['4']) {
      const step = data.steps['4']
      if (step.status === 'completed') stepStatus.value = 'qa_passed'
      else if (step.status === 'qa_review') stepStatus.value = designDoc.value.trim().length >= 50 ? 'qa_review' : 'qa_review'
      else if (step.status === 'in_progress') {
        stepStatus.value = 'executing'
        if (!s4.design_doc && !s4.status) {
          stuckWarning.value = '⚠️ 检测到第四步处于中断状态（无后台任务），请重新执行'
        }
        connectProgressWs()
        startPolling()
        resetStuckTimer()
      }
      else {
        // 步骤状态不明确：优先根据已保存的子流程结果决定显示状态
        const results = s4.sub_flow_results || []
        const hasAnyResult = results.length > 0
        const hasPassed = results.some((r: any) => r.passed)
        const allPassed = results.length === 4 && results.every((r: any) => r.passed)
        const hasQaPassed = s4.qa_passed === true
        if (hasQaPassed) {
          stepStatus.value = 'qa_passed'
        }
        else if (allPassed) {
          stepStatus.value = 'qa_review'
        }
        else if (hasAnyResult) {
          // 任何子流程有结果——展示结果面板，已通过的不允许重复执行
          stepStatus.value = 'qa_review'
        }
        else {
          stepStatus.value = 'idle'
        }
      }
    }
  } catch { stepStatus.value = 'idle' }
  finally { loading.value = false }
})

onUnmounted(() => {
  clearAllTimers()
  if (ws) { ws.onclose = null; ws.close(); ws = null }
})

function startPolling() {
  let emptyCount = 0
  pollTimer = setInterval(async () => {
    try {
      const res = await workflowApi.getStatus(props.projectId) as any
      const data = res?.data || res
      const s4 = data?.step4 || {}
      if (s4.sub_flow_results) {
        emptyCount = 0
        for (const sr of s4.sub_flow_results) {
          const sf = subFlowStates.value[sr.key]
          if (sf) {
            sf.status = sr.passed ? 'passed' : 'failed'
            sf.rounds = sr.rounds || 0
          }
        }
      }
       if (s4.design_doc && s4.design_doc.trim().length >= 50) {
        designDoc.value = s4.design_doc
        stepStatus.value = 'qa_review'
        executing.value = false
        streamStatus.value = '✅ 所有子流程完成'
        clearAllTimers()
        ElMessage.success('架构设计完成，请进行 QA 检验')
      } else if (s4.status === 'error') {
        backendError.value = s4.message || '后端任务执行失败'
        stuckWarning.value = '❌ 后台任务已终止，请点"强制重新执行"恢复'
        streamStatus.value = '❌ 执行失败'
        clearAllTimers()
      } else if (s4.status === 'generating' || data?.steps?.['4']?.status === 'in_progress') {
        emptyCount = 0
        streamStatus.value = s4.message || '🏗️ 4个子流程运行中...'
      } else if (s4.sub_flow_results?.length === 4) {
        // 即使没有 design_doc，但 4 个子流程结果都已返回——可能部分失败
        // 切换到 qa_review 页面展示结果
        stepStatus.value = 'qa_review'
        executing.value = false
        clearAllTimers()
        streamStatus.value = '📋 子流程执行完成，查看结果'
        ElMessage.warning('部分子流程执行完成，请检查结果并续跑未完成项')
      } else {
        // status 为空或不明确——后台可能已死
        emptyCount++
        if (emptyCount >= 6) {  // 30秒无明确状态
          stuckWarning.value = '⚠️ 后端无响应超过30秒，可能已中断。请点"强制重新执行"恢复。'
        }
      }
    } catch {
      emptyCount++
      if (emptyCount >= 6) {
        stuckWarning.value = '⚠️ 无法连接后端超过30秒，请点"强制重新执行"恢复。'
      }
    }
  }, 5000)
}

async function handleExecute() {
  executing.value = true
  restarting.value = false
  error.value = ''
  backendError.value = ''
  stuckWarning.value = ''
  designDoc.value = ''
  stageLog.value = [{ type: 'stage', message: '🚀 4个子流程启动中...' }]
  liveContent.value = ''
  streamStatus.value = '🚀 4个子流程启动中...'
  resetSubFlowStates()
  stepStatus.value = 'executing'
  clearAllTimers()
  try {
    const res = await workflowApi.startStep4(props.projectId) as any
    if (res?.code === 0) {
      streamStatus.value = '🏗️ 4个子流程并行运行中（houwang1→架构/hourong1←→houwang2→前端/hourong2←→houwang3→后端/hourong3←→houwang4→数据库/hourong4）'
      stageLog.value.push({ type: 'stage', message: '📡 已连接后旺1~4号，等待开始生成...' })
      connectProgressWs()
      startPolling()
      resetStuckTimer()
    } else {
      error.value = res?.message || '启动失败'
      stepStatus.value = 'idle'
      executing.value = false
    }
  } catch (e: any) {
    error.value = e?.message || '与后端通信失败，请重试'
    stepStatus.value = 'idle'
    executing.value = false
  }
}

// 续跑未完成项：只运行未通过/未执行的子流程，已通过的不重新运行
async function handleResumeFailed() {
  executing.value = true
  backendError.value = ''
  stuckWarning.value = ''
  error.value = ''
  // 不清除子流程状态——已通过的不重置
  // 只将未通过的子流程标记为生成中
  for (const sf of Object.values(subFlowStates.value)) {
    if (sf.status === 'failed' || sf.status === 'pending') {
      sf.status = 'generating'
      sf.message = '准备重新执行...'
    }
  }
  stepStatus.value = 'executing'
  streamStatus.value = '🔄 续跑未完成项（已通过的不重新运行）...'
  stageLog.value = [{ type: 'stage', message: '🔄 续跑模式启动，跳过已通过检验的文档...' }]
  clearAllTimers()
  if (ws) { ws.onclose = null; ws.close(); ws = null }
  try {
    // resume=true: 后端会跳过已通过的子流程
    const res = await workflowApi.startStep4(props.projectId, true) as any
    if (res?.code === 0) {
      connectProgressWs()
      startPolling()
      resetStuckTimer()
    } else {
      error.value = res?.message || '续跑失败'
      stepStatus.value = 'qa_review'
      executing.value = false
      // 恢复子流程状态
      for (const sf of Object.values(subFlowStates.value)) {
        if (sf.status === 'generating') sf.status = 'pending'
      }
    }
  } catch (e: any) {
    error.value = e?.message || '与后端通信失败'
    stepStatus.value = 'qa_review'
    executing.value = false
    for (const sf of Object.values(subFlowStates.value)) {
      if (sf.status === 'generating') sf.status = 'pending'
    }
  }
}

async function handleRestart() {
  restarting.value = true
  backendError.value = ''
  stuckWarning.value = ''
  error.value = ''
  clearAllTimers()
  if (ws) { ws.onclose = null; ws.close(); ws = null }
  // 强制重置时，清除所有子流程状态
  resetSubFlowStates()
  stepStatus.value = 'executing'
  executing.value = true
  streamStatus.value = '♻️ 续跑模式：跳过已通过项，只重跑未通过子流程...'
  stageLog.value = [{ type: 'stage', message: '♻️ 续跑模式启动，保留已通过检验的文档...' }]
  try {
    const res = await workflowApi.startStep4(props.projectId, true) as any
    if (res?.code === 0) {
      // 恢复续跑模式中已通过的子流程状态
      const preserved = (res.data?.sub_flow_results || []) as Array<{key: string; label: string; passed: boolean}>
      for (const sf of preserved) {
        if (sf.passed && subFlowStates.value[sf.key]) {
          subFlowStates.value[sf.key].status = 'passed'
          subFlowStates.value[sf.key].message = `✅ 已通过（续跑保留）`
          subFlowStates.value[sf.key].detail = ''
        }
      }
      streamStatus.value = '♻️ 续跑中，只重跑未通过项...'
      stageLog.value.push({ type: 'stage', message: '📡 已连接后旺/后荣，等待续跑结果...' })
      connectProgressWs()
      startPolling()
      resetStuckTimer()
    } else {
      error.value = res?.message || '续跑启动失败'
      stepStatus.value = 'idle'
      executing.value = false
      restarting.value = false
    }
  } catch (e: any) {
    error.value = e?.message || '与后端通信失败'
    stepStatus.value = 'idle'
    executing.value = false
    restarting.value = false
  }
}

async function handleRunQA() {
  if (!designDoc.value.trim()) { ElMessage.warning('设计文档内容为空'); return }
  qaLoading.value = true; qaChecked.value = false; qaProgress.value = 0
  try {
    const res = await workflowApi.inspectStep4(props.projectId, designDoc.value) as any
    const data = res?.data || res
    if (data?.dimensions) {
      qaDimensions.value = data.dimensions
      qaPassed.value = !!data.passed
      qaChecked.value = true
    }
    if (data?.passed) ElMessage.success(data.message || '所有检验项目均通过 ✅')
    else ElMessage.warning(data.message || '部分检验项目未通过')
  } catch (e: any) { ElMessage.error('QA 检验失败: ' + (e.message || '未知错误')) }
  finally { qaLoading.value = false; qaProgress.value = 100 }
}

async function handleComplete() {
  loading.value = true
  try {
    const res = await workflowApi.qaStep(props.projectId, 4, 'passed') as any
    const data = res?.data || res
    if (res?.code === 0 || data?.qa) { ElMessage.success('第四步完成！'); stepStatus.value = 'qa_passed' }
    else ElMessage.warning(data?.message || 'QA 提交失败')
  } catch (e: any) { ElMessage.error(e?.message || 'QA 提交失败') }
  finally { loading.value = false }
}

function goBack() { router.push({ name: 'ProjectDetail', params: { projectId: props.projectId } }) }
function goToNext() { router.push({ name: 'ProjectDetail', params: { projectId: props.projectId } }) }
</script>

<style scoped lang="scss">
.step4-view {
  max-width: 1100px; margin: 0 auto; padding: 32px 24px;

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
    &--executing { border-color: #e6a23c; background: #fdf6ec; }
  }

  &__executing-header { display: flex; align-items: center; justify-content: center; gap: 12px; }
  &__executing-status { font-size: 14px; color: #e6a23c; font-weight: 500; margin-bottom: 16px !important; }

  /* ── 4 sub-flow panels (2x2 grid) ── */
  &__subflows {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 16px;
    text-align: left;
  }

  &__subflow-panel {
    background: #fff; border: 1px solid #e4e7ed; border-radius: 8px; padding: 12px;
    transition: all 0.3s ease;
    &.status-generating { border-color: #e6a23c; background: #fffbe6; }
    &.status-reviewing { border-color: #409eff; background: #ecf5ff; }
    &.status-passed { border-color: #67c23a; background: #f0f9eb; }
    &.status-failed { border-color: #f56c6c; background: #fef0f0; }
    &.status-pending { border-color: #dcdfe6; background: #fafafa; }
  }

  &__subflow-header {
    display: flex; align-items: center; gap: 6px; margin-bottom: 6px;
  }
  &__subflow-icon { font-size: 20px; line-height: 1; }
  &__subflow-label { font-weight: 600; font-size: 14px; flex: 1; }
  &__subflow-rounds { font-size: 11px; color: #909399; background: #f5f7fa; padding: 1px 6px; border-radius: 4px; }
  &__subflow-message { font-size: 12px; color: #606266; margin-bottom: 4px; line-height: 1.4; }
  &__subflow-detail { font-size: 11px; color: #909399; margin-bottom: 4px; padding: 4px 8px; background: #f5f7fa; border-radius: 4px; line-height: 1.3; max-height: 40px; overflow: hidden; }
  &__subflow-content {
    max-height: 120px; overflow-y: auto; background: #1a1a2e; color: #e0e0e0; border-radius: 4px; padding: 8px; margin-top: 4px;
    pre { margin: 0; font-size: 11px; line-height: 1.4; white-space: pre-wrap; word-break: break-word; font-family: 'Courier New', monospace; }
  }
  &__subflow-bar { margin-top: 6px; }

  &__executing-actions { display: flex; justify-content: center; gap: 12px; margin-top: 16px; }
  &__stage-collapse { margin-top: 8px; text-align: left; :deep(.el-collapse-item__header) { font-size: 13px; } }

  &__stage-log { max-height: 200px; overflow-y: auto; }
  &__progress-msg { padding: 4px 10px; margin-bottom: 3px; border-radius: 4px; font-size: 12px; line-height: 1.4; background: #fff; border: 1px solid #ebeef5; }
  &__progress-msg.stage { border-left: 3px solid #e6a23c; }
  &__progress-msg.progress { border-left: 3px solid #409eff; color: #606266; }
  &__progress-msg.done { border-left: 3px solid #67c23a; background: #f0f9eb; }
  &__progress-msg.error { border-left: 3px solid #f56c6c; background: #fef0f0; }

  /* ── idle doc preview ── */
  &__doc-list-preview { max-width: 500px; margin: 0 auto 32px; text-align: left; }
  &__doc-type-item {
    display: flex; align-items: center; gap: 12px; padding: 12px 16px; margin-bottom: 8px; background: #f5f7fa; border-radius: 8px;
    &-icon { font-size: 24px; } &-name { font-weight: 500; font-size: 14px; } &-desc { font-size: 12px; color: #909399; margin-top: 2px; }
  }

  /* ── summary cards on qa_review ── */
  &__summary {
    display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap;
  }
  &__summary-card {
    display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 8px; border: 1px solid #e4e7ed; background: #fff; flex: 1; min-width: 160px;
    &.status-passed { border-color: #67c23a; background: #f0f9eb; }
    &.status-failed { border-color: #f56c6c; background: #fef0f0; }
  }
  &__summary-icon { font-size: 24px; }
  &__summary-body { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  &__summary-label { font-weight: 500; font-size: 13px; }
  &__summary-rounds { font-size: 11px; color: #909399; }

  &__result { margin-top: 16px; }
  &__tabs { background: #fff; border: 1px solid #e4e7ed; border-radius: 8px; padding: 16px; }
  &__doc-content { max-height: 600px; overflow-y: auto; pre { white-space: pre-wrap; word-break: break-word; font-size: 13px; line-height: 1.6; margin: 0; } }

  &__qa-section { margin-top: 24px; h3 { margin: 0 0 4px; font-size: 18px; } }
  &__qa-subtitle { color: #909399; font-size: 13px; margin: 0 0 16px; }
  &__qa-loading { text-align: center; padding: 24px; }
  &__qa-dimension { padding: 12px 16px; background: #f5f7fa; border-radius: 6px; margin-bottom: 8px;
    &-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
    &-label { font-weight: 500; font-size: 14px; }
    &-detail { margin: 0; font-size: 13px; color: #606266; }
  }
  &__qa-actions, &__qa-start { text-align: center; margin-top: 16px; }
  &__actions { display: flex; justify-content: center; gap: 12px; }
  &__complete-actions { margin-top: 24px; }
}
</style>
