<template>
  <div class="step3-qa" v-loading="store.loading">
    <div class="step3-qa__header">
      <div class="step3-qa__header-left">
        <el-button :icon="ArrowLeft" text @click="goBack">返回</el-button>
        <div>
          <h1>第三步：需求分析 · QA 检验</h1>
          <p class="step3-qa__subtitle">{{ projectName }} · 后荣（HouRong）QA 检验员</p>
        </div>
      </div>
      <div class="step3-qa__header-right">
        <el-tag type="warning" effect="dark" size="large">QA检验</el-tag>
        <el-button type="primary" size="small" @click="goBackToDiscuss" style="margin-left: 8px;">
          返回需求分析
        </el-button>
      </div>
    </div>

    <div class="step3-qa__card">
      <div class="step3-qa__header-inner">
        <div class="step3-qa__icon">🔍</div>
        <h2>后荣（HouRong）· QA 检验（4子步骤）</h2>
      </div>
      <p class="step3-qa__subtitle-inner">逐项检验需求文档的4个维度，通过后自动推进到下一步</p>

      <div v-if="qaLoading || qaChecked" class="step3-qa__sub-step-progress">
        <div
          v-for="(ss, i) in QA_SUB_STEPS"
          :key="ss.key"
          class="step3-qa__sub-step-item"
          :class="{
            'step3-qa__sub-step-item--done': i < currentSubStep,
            'step3-qa__sub-step-item--active': i === currentSubStep && qaLoading,
            'step3-qa__sub-step-item--pending': i > currentSubStep,
          }"
        >
          <div class="step3-qa__sub-step-indicator">
            <span v-if="i < currentSubStep">✅</span>
            <span v-else-if="i === currentSubStep && qaLoading">🔍</span>
            <span v-else>{{ ss.step }}</span>
          </div>
          <div class="step3-qa__sub-step-label">{{ ss.label }}</div>
        </div>
      </div>

      <div v-if="qaLoading" class="step3-qa__loading">
        <el-progress :percentage="qaProgress" :stroke-width="6" :status="qaProgress >= 100 ? 'success' : 'warning'" />
        <div class="step3-qa__timer">
          <span>⏱ {{ qaElapsed }}</span>
          <span>当前：{{ subStepElapsed }}</span>
          <span>剩余：{{ estimatedRemaining }}</span>
        </div>
        <div class="step3-qa__stream">
          <p v-for="(line, i) in qaStreamLines" :key="i" class="step3-qa__stream-line">{{ line }}</p>
          <p v-if="qaStreamBuffer" class="step3-qa__stream-line step3-qa__stream-line--active">{{ qaStreamBuffer }}<span class="step3-qa__cursor">|</span></p>
        </div>
      </div>

      <div v-else-if="qaChecked" class="step3-qa__dimensions">
        <div class="step3-qa__todolist">
          <div class="step3-qa__todolist-header">
            <div class="step3-qa__todolist-title">
              <span class="step3-qa__todolist-icon">📋</span>
              <span>4子步骤检验报告</span>
            </div>
            <el-tag :type="currentSubStep >= 4 ? 'success' : 'warning'" size="small">
              {{ currentSubStep }}/4 完成
            </el-tag>
          </div>
          <div
            v-for="(ss, idx) in QA_SUB_STEPS"
            :key="ss.key"
            class="step3-qa__todoitem"
            :class="{
              'step3-qa__todoitem--done': subStepResults[idx]?.passed,
              'step3-qa__todoitem--failed': subStepResults[idx] && !subStepResults[idx].passed,
            }"
          >
            <div class="step3-qa__todoitem-checkbox">
              <el-checkbox :model-value="!!subStepResults[idx]?.passed" disabled />
            </div>
            <div class="step3-qa__todoitem-body">
              <div class="step3-qa__todoitem-label">
                子步骤{{ ss.step }}：{{ ss.label }}
                <el-tag v-if="subStepResults[idx]" :type="subStepResults[idx].passed ? 'success' : 'danger'" size="small" effect="plain" style="margin-left: 8px;">
                  得分：{{ subStepResults[idx].score }}
                </el-tag>
              </div>
              <div class="step3-qa__todoitem-detail">
                {{ subStepResults[idx]?.detail || (idx < currentSubStep ? '检验通过 ✅' : '待检验') }}
              </div>
            </div>
            <div class="step3-qa__todoitem-badge">
              <el-tag v-if="subStepResults[idx]?.passed" type="success" size="small" effect="dark">✅ 通过</el-tag>
              <el-tag v-else-if="subStepResults[idx] && !subStepResults[idx].passed" type="danger" size="small" effect="dark">❌ 未通过</el-tag>
              <el-tag v-else-if="idx < currentSubStep" type="success" size="small" effect="dark">✅ 通过</el-tag>
              <el-tag v-else type="info" size="small" effect="dark">⏳ 待检验</el-tag>
            </div>
          </div>
        </div>

        <el-divider />

        <div class="step3-qa__result-area">
          <div v-if="qaPassed && currentSubStep >= 4" class="step3-qa__result step3-qa__result--passed">
            <el-result icon="success" title="全部4个子步骤通过 ✅" sub-title="需求文档已达到验收标准">
              <template #extra>
                <el-button type="primary" @click="handleComplete">进入下一步 ➜</el-button>
              </template>
            </el-result>
          </div>
          <div v-else-if="qaChecked && !qaLoading && currentSubStep < 4" class="step3-qa__result step3-qa__result--failed">
            <el-result icon="error" title="第{{ currentSubStep + 1 }}步未通过" sub-title="请检查后手动修复">
              <template #extra>
                <el-button type="primary" @click="handleRunQA">重新检验</el-button>
                <el-button @click="goBackToDiscuss" style="margin-left:8px;">返回修改</el-button>
              </template>
            </el-result>
          </div>
        </div>
      </div>

      <div v-else class="step3-qa__waiting">
        <p class="step3-qa__waiting-text">后荣将逐项检验以下4个维度，通过后自动推进：</p>
        <div class="step3-qa__dimension-list">
          <div v-for="dim in SRS_DIMENSIONS" :key="dim.key" class="step3-qa__dimension-item">
            <span class="step3-qa__dimension-item-label">{{ dim.label }}</span>
            <span class="step3-qa__dimension-item-desc">{{ dim.description }}</span>
          </div>
        </div>
        <div v-if="qaHasCheckpoint" style="margin-top: 12px;">
          <el-alert title="检测到未完成的QA检验" :description="'已检验 ' + currentSubStep + '/4 个子步骤'" type="warning" show-icon :closable="false" style="margin-bottom: 12px;" />
          <el-button type="warning" size="large" @click="handleRunQA" :loading="qaLoading">
            ⏩ 从断点继续（子步骤{{ currentSubStep + 1 }}）
          </el-button>
        </div>
        <el-button v-else type="primary" size="large" @click="handleRunQA" :loading="qaLoading">
          开始 4子步骤 QA 检验
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRequirementStore } from '@/stores/useRequirementStore'
import { workflowApi } from '@/api/modules/workflow'

interface SubStepResult {
  step: number
  key: string
  label: string
  score: number
  detail: string
  passed: boolean
}

interface Dimension {
  key: string
  label: string
  description: string
}

const QA_CP_PREFIX = 'qa_checkpoint_'

function _qaKey(): string {
  return QA_CP_PREFIX + projectId.value
}

function _saveQaCpToLocal(cp: any) {
  try { localStorage.setItem(_qaKey(), JSON.stringify(cp)) } catch {}
}

function _loadQaCpFromLocal(): any {
  try {
    const raw = localStorage.getItem(_qaKey())
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

function _clearQaCpLocal() {
  try { localStorage.removeItem(_qaKey()) } catch {}
}

const SRS_DIMENSIONS: Dimension[] = [
  { key: 'completeness', label: '完整性', description: '需求文档是否覆盖了所有必要的功能和非功能需求' },
  { key: 'consistency', label: '一致性', description: '文档内容前后是否一致，术语定义是否统一' },
  { key: 'verifiability', label: '可验证性', description: '每个需求是否可量化、可测试、可验证' },
  { key: 'unambiguity', label: '无歧义性', description: '需求描述是否清晰明确，不存在二义性理解' },
]

const QA_SUB_STEPS = [
  { step: 1, key: 'completeness', label: '完整性', desc: '需求文档是否覆盖了所有必要的功能和非功能需求' },
  { step: 2, key: 'consistency', label: '一致性', desc: '文档内容前后是否一致，术语定义是否统一' },
  { step: 3, key: 'verifiability', label: '可验证性', desc: '每个需求是否可量化、可测试、可验证' },
  { step: 4, key: 'unambiguity', label: '无歧义性', desc: '需求描述是否清晰明确，不存在二义性理解' },
]

const router = useRouter()
const route = useRoute()
const store = useRequirementStore()

const projectId = computed(() => route.params.projectId as string)
const projectName = computed(() => route.query.name as string || store.projects.find(p => p.id === projectId.value)?.name || '未命名项目')

const qaLoading = ref(false)
const qaProgress = ref(0)
const qaPassed = ref(false)
const qaChecked = ref(false)
const qaMessage = ref('')
const currentSubStep = ref(0)
const subStepResults = ref<SubStepResult[]>([])
const qaHasCheckpoint = ref(false)
const qaStreamText = ref('')
const qaStreamBuffer = ref('')

const qaStartTime = ref(0)
const qaElapsed = ref('00:00')
const subStepStartTime = ref(0)
const subStepElapsed = ref('00:00')
const subStepDurations = ref<number[]>([])
const estimatedRemaining = ref('--:--')
let qaTimerInterval: ReturnType<typeof setInterval> | null = null

const qaStreamLines = computed(() => qaStreamText.value.split('\n').filter(l => l.trim()))

function _fmtTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function _recordSubStepDuration() {
  const elapsed = Math.floor((Date.now() - subStepStartTime.value) / 1000)
  if (elapsed > 0) subStepDurations.value.push(elapsed)
}

function _estimateRemaining() {
  const d = subStepDurations.value
  const total = 4
  const done = d.length
  if (done === 0) { estimatedRemaining.value = '--:--'; return }
  const avg = d.reduce((a, b) => a + b, 0) / done
  const secs = Math.round(avg * (total - done))
  estimatedRemaining.value = secs < 60 ? `${secs}s` : _fmtTime(secs)
}

function _startQaTimer() {
  qaStartTime.value = Date.now()
  subStepStartTime.value = Date.now()
  qaTimerInterval = setInterval(() => {
    const total = Math.floor((Date.now() - qaStartTime.value) / 1000)
    qaElapsed.value = _fmtTime(total)
    const step = Math.floor((Date.now() - subStepStartTime.value) / 1000)
    subStepElapsed.value = _fmtTime(step)
    _estimateRemaining()
  }, 1000)
}

function _stopQaTimer() {
  if (qaTimerInterval) { clearInterval(qaTimerInterval); qaTimerInterval = null }
}

function getQaWsUrl(): string {
  const token = localStorage.getItem('access_token') || ''
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/step3/qa/${projectId.value}?token=${token}`
}

async function fetchFileContent(filepath: string): Promise<string> {
  try {
    const token = localStorage.getItem('access_token') || ''
    const resp = await fetch('/api/v1/workflow/' + projectId.value + '/step3/read-file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ path: filepath }),
    })
    const data = await resp.json()
    if (data?.code === 0 && data?.data?.content) return data.data.content
  } catch {}
  return `[读取文件失败: ${filepath}]`
}

let qaWs: WebSocket | null = null

async function handleRunQA() {
  if (!docContent || docContent.trim().length < 20) {
    ElMessage.warning('需求文档内容不足，尝试从分片加载...')
    const assembled = await loadShardContent()
    if (assembled && assembled.length >= 20) {
      docContent = assembled
    } else {
      ElMessage.error('需求文档内容为空，无法进行QA检验')
      qaLoading.value = false
      return
    }
  }
  _stopQaTimer()
  qaLoading.value = true
  qaChecked.value = false
  qaStreamText.value = ''
  qaStreamBuffer.value = ''
  subStepDurations.value = []
  _startQaTimer()

  if (qaWs) { qaWs.onclose = null; qaWs.close(); qaWs = null }

  qaHasCheckpoint.value = false
  qaProgress.value = 0
  try {
    const checkWs = new WebSocket(getQaWsUrl())
    await new Promise<void>((resolve) => {
      const timer = setTimeout(() => { checkWs.close(); resolve() }, 5000)
      checkWs.onmessage = (e: MessageEvent) => {
        const m = JSON.parse(e.data)
        if (m.type === 'checkpoint') {
          const cp = m.data || {}
          if (cp.step && cp.step > 0 && cp.step < 4) {
            qaHasCheckpoint.value = true
            currentSubStep.value = Number(cp.step)
            const saved = cp.results || []
            saved.forEach((r: any, i: number) => {
              if (i < 4) subStepResults.value[i] = { step: i + 1, key: r.key||'', label: r.label||'', score: r.score||0, detail: r.detail||'', passed: r.passed||false }
            })
            qaProgress.value = (Number(cp.step) / 4) * 100
            _saveQaCpToLocal(cp)
          }
        }
      }
      checkWs.onopen = () => checkWs.send(JSON.stringify({ action: 'checkpoint' }))
      checkWs.onclose = () => { clearTimeout(timer); resolve() }
      checkWs.onerror = () => { clearTimeout(timer); resolve() }
    })
  } catch {}

  if (qaWs) { qaWs.onclose = null; qaWs.close(); qaWs = null }

  try {
    qaWs = new WebSocket(getQaWsUrl())
    await new Promise<void>((resolve, reject) => {
      let done = false

      qaWs!.onmessage = (event) => {
        const msg = JSON.parse(event.data)

        if (msg.type === 'checkpoint') {
          const cp = msg.data || {}
          if (cp.step && cp.step > 0 && cp.step < 4) {
            qaHasCheckpoint.value = true
            const saved = cp.results || []
            saved.forEach((r: any, i: number) => {
              if (i < 4) {
                subStepResults.value[i] = { step: i + 1, key: r.key || '', label: r.label || '', score: r.score || 0, detail: r.detail || '', passed: r.passed || false }
              }
            })
            currentSubStep.value = Number(cp.step)
            qaProgress.value = (Number(cp.step) / 4) * 100
            _saveQaCpToLocal(cp)
          } else {
            qaHasCheckpoint.value = false
            _clearQaCpLocal()
          }
        }

        if (msg.type === 'progress') {
          if (typeof msg.content === 'string' && msg.content.startsWith('/')) {
            fetchFileContent(msg.content).then(txt => { qaStreamBuffer.value += txt })
          } else {
            qaStreamBuffer.value += msg.content
          }
          qaProgress.value = Math.min(qaProgress.value + 2, 85)
        }

        if (msg.type === 'houxing_chunk') {
          if (typeof msg.content === 'string' && msg.content.startsWith('/')) {
            fetchFileContent(msg.content).then(txt => { qaStreamBuffer.value += txt })
          } else {
            qaStreamBuffer.value += msg.content
          }
        }

        if (msg.type === 'sub_step_start') {
          const d = msg.data
          const newStep = d.step - 1
          if (newStep > currentSubStep.value) {
            currentSubStep.value = newStep
          }
          qaProgress.value = (newStep / d.total_steps) * 100
          subStepStartTime.value = Date.now()
        }

        if (msg.type === 'sub_step_passed') {
          const d = msg.data
          const idx = d.step - 1
          _recordSubStepDuration()
          subStepResults.value[idx] = { step: d.step, key: d.key, label: d.label, score: d.score, detail: d.detail || '检验通过', passed: true }
          currentSubStep.value = Number(d.step)
          qaProgress.value = (Number(d.step) / Number(d.total_steps)) * 100
          // 每个子步骤通过后立即持久化 checkpoint 到 localStorage
          _saveQaCpToLocal({ step: Number(d.step), results: subStepResults.value.slice(0, Number(d.step)).map(r => ({ key: r.key, label: r.label, score: r.score, detail: r.detail, passed: r.passed })) })
        }

        if (msg.type === 'sub_step_failed') {
          const d = msg.data
          const idx = d.step - 1
          _recordSubStepDuration()
          subStepResults.value[idx] = { step: d.step, key: d.key, label: d.label, score: d.score, detail: d.shard_file_defects || d.detail || '检验未通过', passed: false }
          qaChecked.value = true
          qaProgress.value = 75
        }

        if (msg.type === 'error') {
          qaStreamText.value += `\n❌ 错误: ${msg.message}`
          qaChecked.value = true
          if (!done) { done = true; reject(new Error(msg.message)) }
        }

        if (msg.type === 'step_complete') {
          qaPassed.value = true
          qaChecked.value = true
          currentSubStep.value = 4
          _clearQaCpLocal()
          _stopQaTimer()
          if (!done) { done = true; resolve() }
        }
      }

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
        qaWs!.send(JSON.stringify({ action: 'inspect', content: docContent }))
      }
    })

    if (qaPassed.value) {
      ElMessage.success('所有检验项目均通过！即将进入第4步...')
      await handleComplete()
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

async function handleComplete() {
  ElMessage.success('第三步完成！')
  setTimeout(() => {
    router.push({ name: 'ProjectDetail', params: { projectId: projectId.value } })
  }, 1500)
}

function goBack() {
  _clearQaCpLocal()
  router.push({ name: 'ProjectDetail', params: { projectId: projectId.value } })
}

function goBackToDiscuss() {
  _clearQaCpLocal()
  window.location.href = `/step3/${projectId.value}?force=1`
}

let docContent = ''
let shardIndexPath = ''

async function loadShardContent(): Promise<string> {
  try {
    const token = localStorage.getItem('access_token') || ''
    const resp = await fetch('/api/v1/workflow/' + projectId.value + '/step3/shard-index', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: '{}',
    })
    const json = await resp.json()
    const d = json && (json.data || json)
    const shards: { key: string; path: string }[] = (d && d.shards) || []
    if (!shards.length) return ''
    const parts: string[] = []
    for (const shard of shards) {
      if (!shard.path) continue
      try {
        const fResp = await fetch('/api/v1/workflow/' + projectId.value + '/step3/read-file', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
          body: JSON.stringify({ path: shard.path }),
        })
        const fJson = await fResp.json()
        const content = (fJson && (fJson.data || fJson)?.content) || ''
        if (content) parts.push('<!-- CHAPTER:' + shard.key + ' -->\n' + content)
      } catch {}
    }
    return parts.join('\n\n')
  } catch { return '' }
}

async function loadProjectData() {
  try {
    const res = await workflowApi.getStep3Status(projectId.value) as any
    const data = res?.data || res
    if (!data) return
    if (data.doc_content && data.doc_content.length >= 20) docContent = data.doc_content
    if (data.shard_index_path) shardIndexPath = data.shard_index_path
    if (!docContent || docContent.length < 20) {
      const assembled = await loadShardContent()
      if (assembled && assembled.length >= 20) docContent = assembled
    }
    // 优先从 localStorage 加载 checkpoint（页面刷新不丢失）
    let qaCp = _loadQaCpFromLocal()
    if (!qaCp || !qaCp.step || qaCp.step < 1 || qaCp.step >= 4) {
      if (data.qa_checkpoint) {
        qaCp = data.qa_checkpoint
      } else {
        qaCp = null
      }
    }
    if (qaCp) {
      if (qaCp.step && qaCp.step > 0 && qaCp.step < 4) {
        qaHasCheckpoint.value = true
        currentSubStep.value = Number(qaCp.step)
        qaProgress.value = (Number(qaCp.step) / 4) * 100
        const saved = qaCp.results || []
        saved.forEach((r: any, i: number) => {
          if (i < 4) {
            subStepResults.value[i] = { step: i + 1, key: r.key || '', label: r.label || '', score: r.score || 0, detail: r.detail || '', passed: r.passed || false }
          }
        })
        // 缓存到 localStorage
        _saveQaCpToLocal(qaCp)
      }
    }
  } catch {}
}

onMounted(async () => {
  if (!projectId.value) {
    ElMessage.error('缺少项目ID')
    router.push({ name: 'ProjectList' })
    return
  }
  await store.fetchProjects()
  store.selectProject(projectId.value)
  await loadProjectData()
})

onUnmounted(() => {
  _stopQaTimer()
  if (qaWs) {
    qaWs.onclose = null
    qaWs.close()
    qaWs = null
  }
})
</script>

<style scoped lang="scss">
.step3-qa {
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
      h1 { margin: 0; font-family: $font-display; font-size: $display-md-size; font-weight: $display-lg-weight; color: $ink; }
    }
    &-right { flex-shrink: 0; }
  }
  &__subtitle { margin: $spacing-xxs 0 0; font-size: $caption-size; color: $ink-muted-48; }

  &__card {
    max-width: 1240px; width: 100%; margin: 0 auto; background: $canvas;
    border: 1px solid $hairline; border-radius: $radius-lg; text-align: center;
    padding: $spacing-8;
    h2 { font-family: $font-display; font-size: $display-md-size; margin: 0 0 $spacing-xs; }
  }
  &__header-inner { display: flex; align-items: center; justify-content: center; gap: $spacing-xs; }
  &__icon { font-size: 36px; }
  &__subtitle-inner { color: $ink-muted-48; margin: $spacing-xs 0 $spacing-6; }

  &__loading { padding: $spacing-4; p { color: $ink-muted-48; margin-top: $spacing-sm; } }
  &__timer { display: flex; gap: $spacing-4; justify-content: center; margin-top: $spacing-sm; font-size: 13px; color: $ink-muted-48; span { white-space: nowrap; } }
  &__stream {
    max-height: 300px; overflow-y: auto; text-align: left; background: $canvas-parchment;
    border: 1px solid $hairline; border-radius: $radius-sm; padding: $spacing-sm;
    margin-top: $spacing-sm; font-size: $caption-size; line-height: 1.5; color: $ink;
    &-line { margin: 0; white-space: pre-wrap; word-break: break-word; &--active { color: $primary; } }
  }
  &__cursor { animation: blink 1s step-end infinite; }
  @keyframes blink { 50% { opacity: 0; } }

  &__dimensions { text-align: left; padding: 0 $spacing-4 $spacing-4; }
  &__result-area { padding: 0 $spacing-4 $spacing-4; }
  &__result {
    &--passed :deep(.el-result__icon) { --el-result-icon-color: $status-done; }
    &--failed :deep(.el-result__icon) { --el-result-icon-color: $priority-urgent; }
  }

  &__waiting { padding: $spacing-8 $spacing-4;
    &-text { color: $ink-muted-48; margin-bottom: $spacing-4; font-size: $body-size; }
  }

  &__dimension-list { display: flex; flex-direction: column; gap: $spacing-xs; margin-bottom: $spacing-6; text-align: left; }
  &__dimension-item {
    display: flex; flex-direction: column; padding: $spacing-xs $spacing-sm;
    border: 1px solid $hairline; border-radius: $radius-sm; background: $canvas-parchment;
    &-label { font-size: $body-strong-size; font-weight: $body-strong-weight; color: $ink; }
    &-desc { font-size: $fine-print-size; color: $ink-muted-48; }
  }

  &__todolist {
    text-align: left; padding: $spacing-4; background: $canvas-parchment;
    border-radius: $radius-sm; border: 1px solid $hairline;
    &-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: $spacing-sm; padding-bottom: $spacing-sm; border-bottom: 1px solid $hairline; }
    &-title { display: flex; align-items: center; gap: $spacing-xs; font-size: $body-strong-size; font-weight: $body-strong-weight; color: $ink; }
    &-icon { font-size: 18px; }
  }

  &__todoitem {
    display: flex; align-items: flex-start; gap: $spacing-sm; padding: $spacing-sm;
    margin-bottom: $spacing-xs; border: 1px solid $hairline; border-radius: $radius-sm;
    background: $canvas; transition: all 0.2s;
    &--done { border-color: $status-done; background: #f0fdf4; opacity: 0.75; .step3-qa__todoitem-label { text-decoration: line-through; color: $ink-muted-48; } }
    &--failed { border-color: $priority-urgent; background: #fef2f2; }
    &--pending { border-color: $hairline; }
    &-checkbox { flex-shrink: 0; margin-top: 2px; }
    &-body { flex: 1; min-width: 0; }
    &-label { font-size: $body-strong-size; font-weight: $body-strong-weight; color: $ink; margin-bottom: 2px; }
    &-detail { font-size: $fine-print-size; color: $ink-muted-48; line-height: 1.4; white-space: pre-wrap; }
    &-badge { flex-shrink: 0; margin-left: auto; }
  }

  &__sub-step-progress {
    display: flex; align-items: center; justify-content: center; gap: 0;
    padding: $spacing-sm $spacing-8; margin-bottom: $spacing-4;
    background: $canvas-parchment; border: 1px solid $hairline; border-radius: $radius-lg; overflow-x: auto;
  }
  &__sub-step-item {
    display: flex; align-items: center; gap: $spacing-xs; padding: 0 $spacing-sm; position: relative; flex-shrink: 0;
    &::after { content: ''; position: absolute; right: -$spacing-xs; top: 50%; width: 8px; height: 8px; border-right: 2px solid $hairline; border-bottom: 2px solid $hairline; transform: translateY(-50%) rotate(-45deg); }
    &:last-child::after { display: none; }
    &--done { .step3-qa__sub-step-indicator { background: $status-done; color: $on-primary; border-color: $status-done; } .step3-qa__sub-step-label { color: $status-done; } }
    &--active { .step3-qa__sub-step-indicator { background: $primary; color: $on-primary; border-color: $primary; box-shadow: 0 0 0 3px rgba($primary, 0.2); } .step3-qa__sub-step-label { color: $primary; font-weight: 600; } }
    &--pending { .step3-qa__sub-step-indicator { background: $canvas; color: $ink-muted-48; border-color: $hairline; } .step3-qa__sub-step-label { color: $ink-muted-48; } }
  }
  &__sub-step-indicator { width: 28px; height: 28px; border-radius: 50%; border: 2px solid $hairline; display: flex; align-items: center; justify-content: center; font-size: $fine-print-size; font-weight: 600; flex-shrink: 0; }
  &__sub-step-label { font-size: $caption-size; white-space: nowrap; }
}
</style>
