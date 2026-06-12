<template>
  <div class="step4-view" v-loading="loading">
    <div class="step4-view__header">
      <div class="step4-view__header-left">
        <el-button :icon="ArrowLeft" text @click="goBack">返回</el-button>
        <div>
          <h1>第四步：架构设计</h1>
          <p class="step4-view__subtitle">{{ projectName }} · 后旺（HouWang）架构师</p>
        </div>
      </div>
      <div class="step4-view__header-right">
        <el-tag :type="statusTag" effect="dark" size="large">{{ statusLabel }}</el-tag>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon closable class="step4-view__alert" />

    <!-- idle: 待执行 -->
    <div v-if="stepStatus === 'idle'" class="step4-view__card">
      <div class="step4-view__card-icon">🏗️</div>
      <h2>准备执行架构设计</h2>
      <p>后旺（HouWang）将根据 Step3 需求文档自动生成以下设计文档：</p>
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

    <!-- executing: 轮询等待后旺完成 + WebSocket 实时进度 -->
    <div v-if="stepStatus === 'executing'" class="step4-view__card step4-view__card--executing">
      <div class="step4-view__card-icon">🏗️</div>
      <h2>后旺正在生成架构设计方案</h2>
      <p class="step4-view__executing-status">{{ streamStatus }}</p>
      <div class="step4-view__progress">
        <el-progress :percentage="100" :stroke-width="8" status="warning" indeterminate />
      </div>
      <div class="step4-view__executing-hint">
        <div class="step4-view__stage-log">
          <div v-for="(msg, i) in stageLog" :key="i" class="step4-view__progress-msg" :class="msg.type">
            <span v-if="msg.type === 'stage'">📌</span>
            <span v-else-if="msg.type === 'progress'">⏳</span>
            <span v-else-if="msg.type === 'done'">✅</span>
            <span v-else>ℹ️</span>
            {{ msg.message }}
          </div>
        </div>
        <div v-if="liveContent.trim()" class="step4-view__live-content">
          <pre>{{ liveContent }}</pre>
        </div>
      </div>
    </div>

    <!-- qa_review / qa_passed: 展示结果 -->
    <div v-if="stepStatus === 'qa_review' || stepStatus === 'qa_passed'" class="step4-view__result">
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
const stageLog = ref<{ type: string; message: string }[]>([])
const liveContent = ref('')
const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL || `ws://${location.hostname}:8000`

// QA state
const qaLoading = ref(false)
const qaProgress = ref(0)
const qaChecked = ref(false)
const qaPassed = ref(false)
const qaDimensions = ref<{ key: string; label: string; description: string; passed: boolean; detail: string }[]>([])

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

const VITE_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

function getProgressWsUrl(): string {
  const token = localStorage.getItem('access_token') || ''
  const base = import.meta.env.VITE_WS_BASE_URL || `ws://${location.hostname}:8000`
  return `${base}/api/step4/progress/${props.projectId}?token=${encodeURIComponent(token)}`
}

let ws: WebSocket | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null

function connectProgressWs() {
  if (ws) { ws.onclose = null; ws.close(); ws = null }
  try {
    ws = new WebSocket(getProgressWsUrl())
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'stage' || msg.type === 'progress') {
          stageLog.value.push({ type: msg.type, message: msg.message })
        } else if (msg.type === 'content') {
          liveContent.value += msg.content
        } else if (msg.type === 'done') {
          stageLog.value.push({ type: 'done', message: msg.message })
          streamStatus.value = '✅ 架构设计完成'
        } else if (msg.type === 'error') {
          stageLog.value.push({ type: 'error', message: msg.message })
        }
      } catch { /* ignore parse errors */ }
    }
    ws.onclose = () => { ws = null }
    ws.onerror = () => { ws = null }
  } catch { /* ws connection failed, fall back to polling */ }
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await workflowApi.getStatus(props.projectId) as any
    const data = res?.data || res
    const step = data?.steps?.['4']
    const s4 = data?.step4 || {}
    if (s4.design_doc) designDoc.value = s4.design_doc
    if (step) {
      if (step.status === 'completed') stepStatus.value = 'qa_passed'
      else if (step.status === 'qa_review') stepStatus.value = designDoc.value.trim().length >= 50 ? 'qa_review' : 'idle'
      else if (step.status === 'in_progress') { stepStatus.value = 'executing'; connectProgressWs(); startPolling() }
      else stepStatus.value = 'idle'
    }
  } catch { stepStatus.value = 'idle' }
  finally { loading.value = false }
})

onUnmounted(() => {
  if (ws) { ws.onclose = null; ws.close(); ws = null }
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
})

function startPolling() {
  pollTimer = setInterval(async () => {
    try {
      const res = await workflowApi.getStatus(props.projectId) as any
      const data = res?.data || res
      const s4 = data?.step4 || {}
      if (s4.design_doc && s4.design_doc.trim().length >= 50) {
        designDoc.value = s4.design_doc
        stepStatus.value = 'qa_review'
        executing.value = false
        streamStatus.value = '✅ 架构设计完成'
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
        ElMessage.success('架构设计完成，请进行 QA 检验')
      } else if (s4.status === 'error') {
        error.value = s4.message || '生成失败'
        stepStatus.value = 'idle'
        executing.value = false
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
      } else if (s4.status === 'generating' || data?.steps?.['4']?.status === 'in_progress') {
        streamStatus.value = s4.message || '🏗️ 后旺正在生成架构设计方案...'
      }
    } catch { /* poll error, retry next cycle */ }
  }, 5000)
}

async function handleExecute() {
  executing.value = true
  error.value = ''
  designDoc.value = ''
  stageLog.value = [{ type: 'stage', message: '🚀 后旺启动中...' }]
  liveContent.value = ''
  streamStatus.value = '🚀 后旺启动中...'
  stepStatus.value = 'executing'
  try {
    const res = await workflowApi.startStep4(props.projectId) as any
    if (res?.code === 0) {
      streamStatus.value = '🏗️ 后旺正在生成架构设计方案（约30分钟）...'
      stageLog.value.push({ type: 'stage', message: '📡 已连接后旺，等待开始生成...' })
      ElMessage.info('后旺已启动，正在生成设计文档（约30分钟），您可以保持此页面查看进度')
      connectProgressWs()
      startPolling()
    } else {
      error.value = res?.message || '启动失败'
      stepStatus.value = 'idle'
      executing.value = false
    }
  } catch (e: any) {
    error.value = e?.message || '与后旺通信失败，请重试'
    stepStatus.value = 'idle'
    executing.value = false
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
  max-width: 1000px; margin: 0 auto; padding: 32px 24px;

  &__header {
    display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px;
    &-left { display: flex; align-items: flex-start; gap: 16px; h1 { margin: 0; font-size: 24px; font-weight: 600; } }
  }
  &__subtitle { margin: 4px 0 0; color: #909399; font-size: 14px; }
  &__alert { margin-bottom: 16px; }

  &__card {
    text-align: center; padding: 48px 32px; background: #fff; border: 1px solid #e4e7ed; border-radius: 8px;
    h2 { margin: 16px 0 8px; font-size: 20px; font-weight: 600; }
    p { color: #909399; margin: 0 0 24px; }
    &-icon { font-size: 48px; line-height: 1; }
    &--executing { border-color: #e6a23c; background: #fdf6ec; }
  }

  &__executing-status { font-size: 15px; color: #e6a23c; font-weight: 500; margin-bottom: 8px !important; }
  &__executing-hint { margin-top: 24px; text-align: left; width: 1240px; max-width: 1240px; p { margin: 0 !important; font-size: 13px; } }
  &__stage-log { max-height: 180px; overflow-y: auto; margin-bottom: 12px; }
  &__live-content { background: #1a1a2e; color: #e0e0e0; border-radius: 8px; padding: 16px; max-height: 400px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; text-align: left; pre { margin: 0; color: inherit; font: inherit; white-space: pre-wrap; word-break: break-word; } }
  &__progress-msg { padding: 6px 12px; margin-bottom: 4px; border-radius: 6px; font-size: 13px; line-height: 1.5; background: #fff; border: 1px solid #ebeef5; }
  &__progress-msg.stage { border-left: 3px solid #e6a23c; }
  &__progress-msg.progress { border-left: 3px solid #409eff; color: #606266; }
  &__progress-msg.done { border-left: 3px solid #67c23a; background: #f0f9eb; }
  &__progress-msg.error { border-left: 3px solid #f56c6c; background: #fef0f0; }

  &__doc-list-preview { max-width: 500px; margin: 0 auto 32px; text-align: left; }
  &__doc-type-item {
    display: flex; align-items: center; gap: 12px; padding: 12px 16px; margin-bottom: 8px; background: #f5f7fa; border-radius: 8px;
    &-icon { font-size: 24px; } &-name { font-weight: 500; font-size: 14px; } &-desc { font-size: 12px; color: #909399; margin-top: 2px; }
  }

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
