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
          'step3-view__progress-step--active': p.key === innerPhase,
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

    <!-- 上传文档提示 -->
    <div v-if="innerPhase === 'upload'" class="step3-view__upload-prompt">
      <el-alert title="请先上传相关参考文档" type="info" show-icon :closable="false">
        <template #default>
          <p style="margin:0 0 12px">开始需求分析前，请先上传项目相关的参考文档（业务说明、技术文档、竞品分析等）。上传完成后点击"开始生成问卷"。</p>
          <el-upload
            :show-file-list="false"
            :before-upload="handleUploadFile"
            accept=".txt,.md,.pdf,.doc,.docx,.xls,.xlsx,.csv,.json,.xml,.html"
          >
            <el-button type="primary" :icon="Upload">上传参考文档</el-button>
          </el-upload>
          <div v-if="refFiles.length > 0" style="margin-top:12px">
            <el-tag v-for="(rf, i) in refFiles" :key="i" closable :disable-transitions size="small" type="info" @close="removeRefFile(i)" style="margin:0 4px 4px 0">
              📎 {{ rf.name }}
            </el-tag>
          </div>
          <el-button v-if="refFiles.length > 0 && !questionnaireSubmitted" type="primary" style="margin-top:12px" @click="startGenerateQuestionnaire" :disabled="chatLoading">
            🧠 开始生成问卷
          </el-button>
        </template>
      </el-alert>
    </div>

    <el-alert v-if="store.error" :title="store.error" type="error" show-icon closable class="step3-view__alert" />

    <div v-if="innerPhase !== 'qa' && innerPhase !== 'upload'" class="step3-view__chat-section">
      <!-- 左侧：对话框（问卷、SRS生成、修改讨论都在这里） -->
      <div class="step3-view__chat-panel">
        <div class="step3-view__panel-header">
          <h3>
            <span class="step3-view__houxing-icon">📋</span>
            后兴（HouXing）· 需求分析师
          </h3>
          <div class="step3-view__panel-actions">
            <el-tag v-if="srsGenerating" type="warning" size="small" effect="plain">📄 生成SRS中...</el-tag>
            <el-tag v-else-if="questionnaireReady && !srsDone" type="primary" size="small" effect="plain">🧠 {{ questions.length || totalQuestions }} 题</el-tag>
            <el-tag v-else-if="srsDone" type="success" size="small" effect="plain">✅ SRS已生成</el-tag>
            <el-tag v-else type="info" size="small" effect="plain">{{ wsStatus }}</el-tag>
            <el-button v-if="!questionnaireSubmitted && !questionnaireReady && !srsDone && !chatLoading" size="small" type="primary" plain @click="startGenerateQuestionnaire">生成问卷</el-button>
          </div>
        </div>

        <div class="step3-view__chat" ref="chatRef">
          <!-- 加载中 -->
          <div v-if="questionnaireGenerating && !questionnaireReady" class="step3-view__chat-empty">
            <div class="step3-view__empty-icon">🧠</div>
            <p>后兴正在使用头脑风暴法生成需求调研问卷...</p>
            <el-progress :percentage="100" :stroke-width="6" :show-text="false" status="warning" indeterminate />
          </div>
          <div v-else-if="chatMessages.length === 0 && !chatLoading && !questionnaireReady && !srsDone && docsUploaded" class="step3-view__chat-empty">
            <div class="step3-view__empty-icon">📋</div>
            <p>正在准备生成问卷...</p>
          </div>

          <!-- 消息列表：问卷 + 对话 -->
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
              <!-- 如果是问卷消息，逐题显示 -->
              <div v-if="msg.isForm" class="step3-view__form-wrap">
                <div v-if="questions.length > 1" class="step3-view__question-indicator">{{ currentQIndex + 1 }} / {{ questions.length }}</div>
                <div v-html="currentQuestionHtml" class="step3-view__form-content"></div>
              </div>
              <!-- 普通消息 -->
              <div v-else v-html="renderContent(msg.content)"></div>
            </div>
          </div>

          <!-- 流式展示（问卷生成或SRS生成中） -->
          <div v-if="srsStreamContent && (srsGenerating || !questionnaireReady)" class="step3-view__srs-stream">
            <pre>{{ srsStreamContent }}</pre>
          </div>

          <!-- 正在思考 -->
          <div v-if="chatLoading && !srsGenerating" class="step3-view__chat-msg houxing">
            <div class="step3-view__chat-avatar">📋</div>
            <div class="step3-view__chat-bubble step3-view__chat-thinking">
              <span class="dot-pulse">{{ questionnaireGenerating ? '后兴正在使用头脑风暴法生成问卷' : '后兴正在处理您的请求' }}<span>.</span><span>.</span><span>.</span></span>
            </div>
          </div>
          <!-- 错误提示 -->
          <div v-if="chatError" class="step3-view__chat-msg system">
            <div class="step3-view__chat-avatar">⚠️</div>
            <div class="step3-view__chat-bubble" style="color:#e6a23c;border-color:#e6a23c;">
              <p>❌ {{ chatError }}</p>
              <el-button size="small" type="warning" @click="chatError=''; questionnaireSubmitted ? retrySrsGeneration() : retryQuestionnaire()">
                {{ questionnaireSubmitted ? '重新生成SRS文档' : '重试' }}
              </el-button>
            </div>
          </div>

          <!-- SRS 生成失败重试横幅 -->
          <div v-if="questionnaireSubmitted && !srsDone && !srsGenerating && !chatError" class="step3-view__chat-msg system">
            <div class="step3-view__chat-avatar">⚠️</div>
            <div class="step3-view__chat-bubble" style="color:#e6a23c;border-color:#e6a23c;">
              <p>❌ SRS 需求文档生成失败</p>
              <el-button size="small" type="warning" @click="retrySrsGeneration()">重新生成SRS文档</el-button>
            </div>
          </div>
        </div>

        <!-- 问卷导航：逐题作答 -->
        <div v-if="questionnaireReady && !srsGenerating && !srsDone && questions.length > 0" class="step3-view__questionnaire-actions">
          <div class="step3-view__question-nav">
            <el-button v-if="currentQIndex > 0" @click="prevQuestion" :disabled="chatLoading">上一题</el-button>
            <span class="step3-view__question-counter">{{ currentQIndex + 1 }} / {{ questions.length }}</span>
            <el-button v-if="currentQIndex < questions.length - 1" type="primary" @click="nextQuestion" :disabled="chatLoading">下一题</el-button>
            <el-button v-else type="primary" size="large" @click="handleSubmitAnswers" :disabled="chatLoading" class="step3-view__action-btn">
              ✅ 提交答案
            </el-button>
          </div>
        </div>

      </div>

      <!-- 右侧面板：分片索引表 / 文档列表 -->
      <div class="step3-view__summary-panel">
        <div class="step3-view__panel-header">
          <h3>
            <span class="step3-view__summary-icon">📄</span>
            {{ shardIndex.length > 0 ? '分片索引表' : '需求文档' }}
          </h3>
          <el-tag v-if="srsDone" type="success" size="small">已生成</el-tag>
          <el-tag v-else type="info" size="small">待生成</el-tag>
        </div>
        <div class="step3-view__summary-content">
          <!-- 分片索引表 -->
          <div v-if="shardIndex.length > 0" class="step3-view__shard-index">
            <div class="step3-view__shard-index-header">
              <span>📋 共 {{ shardIndex.length }} 个分片</span>
            </div>
            <div class="step3-view__shard-index-table">
              <div class="step3-view__shard-index-row step3-view__shard-index-row--header">
                <span class="step3-view__shard-index-col-idx">#</span>
                <span class="step3-view__shard-index-col-path">文件路径</span>
              </div>
              <div
                v-for="(shard, i) in shardIndex"
                :key="shard.key"
                class="step3-view__shard-index-row"
                style="cursor:pointer"
                @click="previewShard(shard)"
              >
                <span class="step3-view__shard-index-col-idx">{{ i + 1 }}</span>
                <span class="step3-view__shard-index-col-path step3-view__shard-index-col-path--clickable">{{ shard.path }}</span>
              </div>
            </div>
            <div v-if="shardIndexContent" class="step3-view__shard-index-preview">
              <pre>{{ shardIndexContent }}</pre>
            </div>
          </div>

          <div v-else class="step3-view__doc-empty">
            <p>后兴将生成需求调研问卷，待您回答完毕后自动生成SRS需求文档。</p>
          </div>
        </div>
        <div class="step3-view__summary-actions">
          <el-button
            v-if="srsDone && !qaResult"
            type="primary"
            size="large"
            @click="handleRequestQA"
            :loading="qaInProgress"
            class="step3-view__action-btn"
          >
            🔍 提交QA检验
          </el-button>
          <div v-if="qaResult" class="step3-view__qa-result">
            <el-alert
              :title="qaResult.passed ? '✅ QA检验通过' : '❌ QA检验未通过'"
              :type="qaResult.passed ? 'success' : 'error'"
              show-icon
              :closable="false"
            >
              <template #default>
                <p>平均得分: {{ qaResult.avg_score?.toFixed(1) }}</p>
                <p>{{ qaResult.message }}</p>
              </template>
            </el-alert>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部输入框：内联在 chat-section 中，不用 Teleport 避免影响 app-main 布局 -->
    <div v-if="innerPhase !== 'qa' && innerPhase !== 'upload' && !srsGenerating" class="step3-chat-input">
      <div class="step3-chat-input__refs" v-if="refFiles.length > 0">
        <el-tag v-for="(rf, i) in refFiles" :key="i" closable :disable-transitions size="small" type="info" @close="removeRefFile(i)">
          📎 {{ rf.name }}
        </el-tag>
      </div>
      <div class="step3-chat-input__row">
        <el-upload
          :show-file-list="false"
          :before-upload="handleUploadFile"
          accept=".txt,.md,.pdf,.doc,.docx,.xls,.xlsx,.csv,.json,.xml,.html"
        >
          <el-button size="default" :disabled="chatLoading" class="step3-chat-input__upload-btn">
            <el-icon><Upload /></el-icon>
          </el-button>
        </el-upload>
        <el-input
          v-model="chatInput"
          type="textarea"
          :rows="2"
          :placeholder="srsDone ? '输入修改意见或补充说明...' : '输入问题或补充说明...'"
          :disabled="chatLoading"
          @keyup.enter.ctrl="handleSendChat"
        />
        <el-button
          type="primary"
          size="large"
          :loading="chatLoading"
          :disabled="!chatInput.trim() || chatLoading"
          @click="handleSendChat"
          class="step3-view__send-btn"
        >
          <el-icon><Promotion /></el-icon>
          发送
        </el-button>
      </div>
    </div>

    <div v-if="innerPhase === 'qa'" class="step3-view__submit-section">
      <div class="step3-view__submit-card">
        <div class="step3-view__submit-header">
          <div class="step3-view__submit-icon">🔍</div>
          <h2>QA 检验结果</h2>
        </div>
        <p class="step3-view__submit-subtitle">后荣已对 SRS 需求文档完成质量检验</p>

        <div v-if="qaResult" class="step3-view__qa-detail">
          <el-alert
            :title="qaResult.passed ? '✅ QA检验通过' : '❌ QA检验未通过'"
            :type="qaResult.passed ? 'success' : 'error'"
            show-icon
            :closable="false"
          >
            <template #default>
              <p style="margin:8px 0">平均得分: {{ qaResult.avg_score?.toFixed(1) }}</p>
              <p style="margin:8px 0">{{ qaResult.message }}</p>
            </template>
          </el-alert>

          <div v-if="qaResult.dimensions" class="step3-view__qa-dimensions" style="margin-top:16px">
            <h4>各维度评分</h4>
            <div v-for="dim in qaResult.dimensions" :key="dim.key" class="step3-view__qa-dim-item" style="margin:8px 0;padding:8px;border:1px solid #eee;border-radius:4px">
              <div style="display:flex;justify-content:space-between">
                <strong>{{ dim.label }}</strong>
                <el-tag :type="dim.passed ? 'success' : 'danger'" size="small">{{ dim.score }}分</el-tag>
              </div>
              <p style="margin:4px 0 0;font-size:13px;color:#666">{{ dim.detail }}</p>
            </div>
          </div>
        </div>

        <div v-else-if="qaInProgress" style="text-align:center;padding:40px">
          <el-progress :percentage="100" :stroke-width="6" :show-text="false" :status="'warning'" indeterminate />
          <p style="margin-top:16px">后荣正在进行QA检验...</p>
        </div>

        <div class="step3-view__submit-actions" style="margin-top:20px">
          <el-button size="large" @click="backToDiscuss">返回修改</el-button>
          <el-button v-if="qaResult?.passed" type="success" size="large" @click="handleComplete">✅ 完成第三步</el-button>
          <el-button v-else-if="qaResult && !qaResult.passed" type="primary" size="large" @click="handleRequestQA">🔄 重新检验</el-button>
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

    <el-dialog v-model="shardPreviewVisible" :title="'分片预览: ' + shardPreviewTitle" width="800px">
      <div class="step3-view__doc-preview-dialog">
        <pre>{{ shardPreviewContent }}</pre>
      </div>
      <template #footer>
        <el-button @click="shardPreviewVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <div v-if="innerPhase === 'complete'" class="step3-view__complete-section">
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
import { ArrowLeft, Promotion, View, Upload } from '@element-plus/icons-vue'
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
const questionnaireRef = ref<HTMLElement | null>(null)
const chatMessages = ref<ChatMessage[]>([])
const chatRound = ref(0)
const chatLoading = ref(false)
const currentPhase = ref('discuss')
const docContent = ref('')

// Questionnaire state
const questionnaireReady = ref(false)
const questionnaireSubmitted = ref(false)
const questionnaireGenerating = ref(false)
const showRetry = ref(false)
const wsStatus = ref('连接中...')
const chatError = ref('')
const refFiles = ref<{ name: string; path?: string; size?: number }[]>([])
const totalQuestions = ref(0)

// 逐题显示
const questions = ref<string[]>([])
const allQids = ref<string[]>([])
const currentQIndex = ref(0)
const answers = ref<Record<string, string>>({})
const lastSubmittedAnswers = ref<Record<string, string>>({})
let _wrapperStart = ''
let _wrapperEnd = ''
const currentQuestionHtml = computed(() => {
  if (questions.value.length === 0) return ''
  return _wrapperStart + questions.value[currentQIndex.value] + _wrapperEnd
})
const srsGenerating = ref(false)
const srsDone = ref(false)
const srsStreamContent = ref('')
const srsProgress = ref(0)
const shardIndex = ref<{ key: string; title: string; path: string; summary: string; has_content: boolean }[]>([])
const shardIndexPath = ref('')
const shardIndexContent = ref('')

const docsUploaded = ref(false)
const qaInProgress = ref(false)
const qaResult = ref<any>(null)
const submitting = ref(false)
const savedDocPath = ref('')
const docPreviewVisible = ref(false)
const shardPreviewVisible = ref(false)
const shardPreviewContent = ref('')
const shardPreviewTitle = ref('')

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
  { key: 'upload', label: '上传文档' },
  { key: 'questionnaire', label: '填写问卷' },
  { key: 'srs_ready', label: 'SRS生成' },
  { key: 'qa', label: 'QA检验' },
]

const innerPhase = ref<'upload' | 'questionnaire' | 'srs_ready' | 'qa'>('upload')

const phaseIndex = computed(() => {
  const idx = phases.findIndex(p => p.key === innerPhase.value)
  return idx >= 0 ? idx : 0
})

const phaseLabel = computed(() => {
  const p = phases.find(p => p.key === innerPhase.value)
  return p?.label || innerPhase.value
})

const phaseTagType = computed(() => {
  const map: Record<string, string> = {
    upload: 'info',
    questionnaire: 'primary',
    srs_ready: 'success',
    qa: 'warning',
  }
  return map[innerPhase.value] || 'info'
})



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

  ws.onmessage = async (event) => {
    const msg = JSON.parse(event.data)

    if (msg.type === 'status') {
      docsUploaded.value = msg.data.docs_uploaded
      questionnaireReady.value = msg.data.questionnaire_generated
      srsDone.value = msg.data.srs_generated
      const answersSubmitted = msg.data.answers_submitted
      if (msg.data.srs_generated) {
        innerPhase.value = 'srs_ready'
        questionnaireSubmitted.value = true
        chatLoading.value = false
        await refreshShardIndex()
      } else if (answersSubmitted) {
        // 问卷已提交：禁止回到问卷环节，显示错误状态
        innerPhase.value = 'srs_ready'
        questionnaireSubmitted.value = true
        questionnaireGenerating.value = false
        chatLoading.value = false
        // 不显示问卷 HTML，只提示用户 SRS 生成失败
        const hasErr = chatMessages.value.some(m => m.isError)
        if (!hasErr) {
          chatMessages.value.push({
            role: 'system',
            content: '⚠️ 问卷已提交，但 SRS 文档生成失败。请联系管理员。',
            isError: true,
          })
        }
      } else if (msg.data.questionnaire_generated && msg.data.questionnaire_html) {
        innerPhase.value = 'questionnaire'
        questionnaireReady.value = true
        questionnaireGenerating.value = false
        totalQuestions.value = msg.data.question_count || 0
        chatLoading.value = false
        const hasForm = chatMessages.value.some(m => m.isForm)
        if (!hasForm) {
          parseQuestionnaireHtml(msg.data.questionnaire_html)
          chatMessages.value.push({ role: 'houxing', content: msg.data.questionnaire_html, started_at: nowStr(), isForm: true })
        }
      } else if (msg.data.docs_uploaded && !msg.data.questionnaire_generated) {
        // 已有上传文档且未生成过问卷 → 自动开始生成问卷
        innerPhase.value = 'questionnaire'
        questionnaireGenerating.value = true
        chatLoading.value = true
        const payload = JSON.stringify({ action: 'generate_questionnaire' })
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(payload)
        }
      } else {
        innerPhase.value = 'upload'
        chatLoading.value = false
      }
      scrollToBottom()
      return
    }

    if (msg.type === 'docs_status') {
      docsUploaded.value = msg.data.uploaded
      return
    }

    if (msg.type === 'qa_result') {
      qaInProgress.value = false
      qaResult.value = msg.data
      chatLoading.value = false
      // QA完成后刷新分片索引表（此时后端已将完整文档拆分为分片）
      await refreshShardIndex()
      if (msg.data.passed) {
        ElMessage.success('✅ QA检验通过!')
      } else {
        ElMessage.warning('QA检验未通过，请根据意见修改后重试')
      }
      return
    }

    if (msg.type === 'enter_qa') {
      qaInProgress.value = false
      chatLoading.value = false
      ElMessage.success('正在进入QA检验阶段...')
      setTimeout(() => {
        router.push({ name: 'Step3Qa', params: { projectId: projectId.value } })
      }, 800)
      return
    }

    // 子Agent状态更新（SRS生成进度）
    if (msg.type === 'subagent_status') {
      chatMessages.value.push({ role: 'houxing', content: msg.data.message, started_at: nowStr() })
      scrollToBottom()
      return
    }

    if (msg.type === 'subagent_progress') {
      const last = chatMessages.value[chatMessages.value.length - 1]
      if (last && last.role === 'houxing' && last.content.includes('子Agent')) {
        last.content = msg.data.message
        last.ended_at = nowStr()
      } else {
        chatMessages.value.push({ role: 'houxing', content: msg.data.message, started_at: nowStr() })
      }
      scrollToBottom()
      return
    }

    if (msg.type === 'questionnaire') {
      console.log('[Step3] 收到问卷:', msg.question_count, '题, HTML长度:', (msg.content || '').length)
      chatError.value = ''
      srsStreamContent.value = ''
      questionnaireReady.value = true
      questionnaireGenerating.value = false
      totalQuestions.value = msg.question_count || 0
      chatLoading.value = false
      parseQuestionnaireHtml(msg.content || '')
      const formMsg: any = { role: 'houxing', content: msg.content || '', started_at: nowStr(), isForm: true }
      chatMessages.value.push(formMsg)
      try { localStorage.setItem(`step3_q_${projectId.value}`, '1') } catch {}
      saveChatSession()
      scrollToBottom()
      return
    }

    if (msg.type === 'chunk') {
      if (srsGenerating.value) {
        srsStreamContent.value += msg.content
        srsProgress.value = Math.min(srsProgress.value + 3, 90)
      } else {
        const last = chatMessages.value[chatMessages.value.length - 1]
        if (last && last.role === 'houxing' && last.content !== '') {
          last.content += msg.content
        } else {
          chatMessages.value.push({ role: 'houxing', content: msg.content, started_at: nowStr() })
        }
      }
      scrollToBottom()
    }

    function parseIndexToShards(indexContent: string): { key: string; title: string; path: string; summary: string; has_content: boolean }[] {
      const lines = (indexContent || '').split('\n')
      const result: { key: string; title: string; path: string; summary: string; has_content: boolean }[] = []
      let inTable = false
      for (const line of lines) {
        if (line.startsWith('|') && line.includes('---')) { inTable = true; continue }
        if (!inTable || !line.startsWith('|')) continue
        const cols = line.split('|').map(c => c.trim()).filter(Boolean)
        if (cols.length >= 2) {
          result.push({
            key: cols[0],
            path: cols.length >= 2 ? cols[1] : '',
            summary: cols.length >= 3 ? cols[2] || '' : '',
            title: cols[0],
            has_content: true,
          })
        }
      }
      return result
    }

    function buildShardIndexFromFiles(files: Record<string, string>): { key: string; title: string; path: string; summary: string; has_content: boolean }[] {
      return Object.entries(files).map(([key, path]) => ({ key, title: key, path, summary: '', has_content: true }))
    }

    async function refreshShardIndex() {
      try {
        const res = await workflowApi.getShardIndex(projectId.value, {}) as any
        const data = res?.data || res
        if (data?.shards?.length > 0) {
          shardIndex.value = data.shards.map((s: any) => ({
            key: s.key,
            title: s.title || s.key,
            path: s.path || '',
            summary: s.summary || '',
            has_content: s.has_content ?? true,
          }))
        }
        if (data?.index_content) {
          shardIndexContent.value = data.index_content
        }
        if (data?.index_path) {
          shardIndexPath.value = data.index_path
        }
      } catch {
        // 静默失败，保持现有 shardIndex
      }
    }

    if (msg.type === 'srs_generated') {
      srsGenerating.value = false
      srsDone.value = true
      srsProgress.value = 100
      chatLoading.value = false
      innerPhase.value = 'srs_ready'
      srsStreamContent.value = ''
      const lastMsg = chatMessages.value[chatMessages.value.length - 1]
      if (lastMsg && lastMsg.role === 'houxing' && lastMsg.content.includes('正在生成SRS')) {
        lastMsg.content = '✅ SRS需求文档已由子Agent生成完毕'
        lastMsg.ended_at = nowStr()
      }
      // QA前只显示单个文档路径，不分片
      shardIndex.value = [{
        key: 'full',
        title: '完整SRS文档',
        path: msg.data.path,
        summary: '',
        has_content: true,
      }]
      saveChatSession()
    }

    // 兼容旧版 shards_saved（过渡期保留）
    if (msg.type === 'shards_saved') {
      srsGenerating.value = false
      srsDone.value = true
      srsProgress.value = 100
      chatLoading.value = false
      innerPhase.value = 'srs_ready'
      srsStreamContent.value = ''
      const lastMsg = chatMessages.value[chatMessages.value.length - 1]
      if (lastMsg && lastMsg.role === 'houxing' && lastMsg.content.includes('正在生成SRS')) {
        lastMsg.content = '✅ SRS需求文档已由子Agent生成完毕'
        lastMsg.ended_at = nowStr()
      }
      await refreshShardIndex()
      saveChatSession()
    }

    if (msg.type === 'shards_updated') {
      chatLoading.value = false
      await refreshShardIndex()
      saveChatSession()
      ElMessage.success('SRS文档已更新')
    }

    if (msg.type === 'done') {
      const last = chatMessages.value[chatMessages.value.length - 1]
      if (last && last.role === 'houxing') last.ended_at = nowStr()
      chatLoading.value = false
      if (srsGenerating.value) {
        srsProgress.value = 95
      }
      if (srsDone.value) {
        innerPhase.value = 'srs_ready'
      }
      saveChatSession()
    }

    if (msg.type === 'error') {
      console.error('[Step3] 服务端错误:', msg.message)
      ElMessage.error(msg.message || '后兴通信失败')
      chatLoading.value = false
      srsGenerating.value = false
      questionnaireGenerating.value = false
      chatError.value = msg.message || '后兴无响应，请稍后重试'
    }
  }

  ws.onopen = () => {
    wsStatus.value = '已连接'
    pendingMessages = []
    chatLoading.value = true
    ws.send(JSON.stringify({ action: 'start' }))
    introSent = true
  }

  ws.onclose = () => {
    wsStatus.value = '已断开'
    ws = null
    if (chatLoading.value) {
      reconnectTimer = setTimeout(connectWebSocket, 3000)
    }
  }

  ws.onerror = () => {
    wsStatus.value = '连接失败'
    ws?.close()
  }
}

async function startGenerateQuestionnaire() {
  if (questionnaireSubmitted.value) {
    ElMessage.warning('问卷已提交，不可重新生成')
    return
  }
  chatLoading.value = true
  questionnaireGenerating.value = true
  innerPhase.value = 'questionnaire'
  srsStreamContent.value = ''
  const payload = JSON.stringify({ action: 'generate_questionnaire' })
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(payload)
  } else {
    pendingMessages.push(payload)
    connectWebSocket()
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

async function saveChatSession() {
  if (!projectId.value) return
  try {
    await workflowApi.saveStep3Artifacts(projectId.value, {
      chat_messages: chatMessages.value.map(m => ({ role: m.role, content: m.content, started_at: m.started_at, ended_at: m.ended_at, isForm: m.isForm })),
      chat_round: chatRound.value,
      doc_content: docContent.value,
      current_phase: innerPhase.value,
      saved_doc_path: savedDocPath.value,
      extracted_docs: extractedDocs.value.map(d => ({ id: d.id, name: d.name, content: d.content, selected: d.selected })),
      doc_save_counter: docSaveCounter,
      questionnaire_ready: questionnaireReady.value,
      total_questions: totalQuestions.value,
      srs_done: srsDone.value,
      shard_index: shardIndex.value,
      shard_index_path: shardIndexPath.value,
      shard_index_content: shardIndexContent.value,
      uploaded_refs: refFiles.value.map(r => ({ name: r.name, path: r.path, size: r.size })),
    })
  } catch {
    // 静默保存失败
  }
}

async function restoreChatSession() {
  try {
    const res = await workflowApi.getStep3Status(projectId.value) as any
    const data = res?.data || res
    if (!data) return
    if (data?.chat_messages?.length > 0) {
      chatMessages.value = data.chat_messages.map((m: any) => ({
        role: m.role, content: m.content,
        started_at: m.started_at, ended_at: m.ended_at,
        isForm: m.isForm === true || (m.role === 'houxing' && typeof m.content === 'string' && m.content.includes('brain-q')),
      }))
      chatRound.value = data.chat_round || 0
    }
    if (data.doc_content) {
      docContent.value = data.doc_content
    }
    // 根据SRS状态设置阶段
    if (data.srs_done) {
      innerPhase.value = 'srs_ready'
    } else if (data.chat_checkpoint?.answers_submitted) {
      // 问卷已提交但SRS未生成（失败状态），禁止回到问卷环节
      innerPhase.value = 'srs_ready'
      questionnaireSubmitted.value = true
    } else if (data.questionnaire_ready || data.questionnaire_html) {
      innerPhase.value = 'questionnaire'
    } else if (data.uploaded_refs?.length > 0) {
      innerPhase.value = 'questionnaire'
    } else {
      innerPhase.value = 'upload'
    }
    if (data.saved_doc_path) {
      savedDocPath.value = data.saved_doc_path
    }
    if (data.extracted_docs) {
      extractedDocs.value = data.extracted_docs
    }
    if (typeof data.doc_save_counter === 'number') {
      docSaveCounter = data.doc_save_counter
    }
    // 恢复问卷状态（优先服务器存档，其次 localStorage）
    if (typeof data.questionnaire_ready === 'boolean') {
      questionnaireReady.value = data.questionnaire_ready
    } else if (data.questionnaire_html) {
      questionnaireReady.value = true
    } else {
      try {
        const ls = localStorage.getItem(`step3_q_${projectId.value}`)
        if (ls === '1') questionnaireReady.value = true
      } catch {}
    }
    if (typeof data.total_questions === 'number') {
      totalQuestions.value = data.total_questions
    }
    if (typeof data.srs_done === 'boolean') {
      srsDone.value = data.srs_done
      if (data.srs_done) questionnaireSubmitted.value = true
    }
    if (data.shard_index) {
      shardIndex.value = data.shard_index
    }
    if (data.shard_index_path) {
      shardIndexPath.value = data.shard_index_path
    }
    if (data.shard_index_content) {
      shardIndexContent.value = data.shard_index_content
    }
    if (chatMessages.value.length > 0 || questionnaireReady.value) {
      introSent = true
    }
    // 恢复上传的文件清单
    if (data.uploaded_refs?.length > 0) {
      refFiles.value = data.uploaded_refs
    }
    // 再从后端同步已上传文件列表（确保完整）
    try {
      const refsRes = await workflowApi.listStep3Refs(projectId.value) as any
      const refsData = refsRes?.data || refsRes
      if (refsData?.refs?.length > 0) {
        const serverRefs = refsData.refs.map((r: any) => ({ name: r.name, path: r.path, size: r.size }))
        // 合并：以后端为准，保留前端已有的
        const merged = [...serverRefs]
        for (const rf of refFiles.value) {
          if (!merged.find(m => m.name === rf.name)) merged.push(rf)
        }
        refFiles.value = merged
      }
    } catch {}
  } catch {
    // 静默恢复失败
  }
}

function parseQuestionnaireHtml(html: string) {
  const parser = new DOMParser()
  const doc = parser.parseFromString(html, 'text/html')
  const wrapper = doc.body.firstElementChild
  if (!wrapper) { questions.value = [html]; return }

  const brainQs = wrapper.querySelectorAll('.brain-q')
  if (brainQs.length === 0) { questions.value = [html]; return }

  const innerHtml = wrapper.innerHTML
  const qHtmls: string[] = []
  const qids: string[] = []
  brainQs.forEach((q) => {
    qHtmls.push((q as HTMLElement).outerHTML)
    const qid = q.getAttribute('data-qid')
    if (qid) qids.push(qid)
  })

  const firstIdx = innerHtml.indexOf(qHtmls[0])
  _wrapperStart = innerHtml.substring(0, firstIdx)

  const lastQ = qHtmls[qHtmls.length - 1]
  const lastIdx = innerHtml.indexOf(lastQ) + lastQ.length
  _wrapperEnd = innerHtml.substring(lastIdx)

  questions.value = qHtmls
  allQids.value = qids
  currentQIndex.value = 0
}

function saveCurrentAnswer() {
  const qEl = document.querySelector('.step3-view__form-content .brain-q')
  if (!qEl) return
  const qid = qEl.getAttribute('data-qid')
  if (!qid) return
  const checked = qEl.querySelector('input:checked') as HTMLInputElement
  const textInput = qEl.querySelector('textarea, input[type="text"]') as HTMLInputElement | HTMLTextAreaElement
  if (checked) {
    answers.value[qid] = checked.value
  } else if (textInput && textInput.value.trim()) {
    answers.value[qid] = textInput.value.trim()
  }
}

function restoreCurrentAnswer() {
  const qid = allQids.value[currentQIndex.value]
  if (!qid) return
  const val = answers.value[qid]
  if (!val) return
  nextTick(() => {
    const qEl = document.querySelector(`.step3-view__form-content .brain-q[data-qid="${qid}"]`)
    if (!qEl) return
    const radio = qEl.querySelector(`input[value="${val}"]`) as HTMLInputElement
    if (radio) { radio.checked = true; return }
    const textInput = qEl.querySelector('textarea, input[type="text"]') as HTMLInputElement
    if (textInput) { textInput.value = val }
  })
}

function nextQuestion() {
  saveCurrentAnswer()
  if (currentQIndex.value < questions.value.length - 1) {
    currentQIndex.value++
    restoreCurrentAnswer()
  }
}

function prevQuestion() {
  saveCurrentAnswer()
  if (currentQIndex.value > 0) {
    currentQIndex.value--
    restoreCurrentAnswer()
  }
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
    if (data?.code === 0 && data?.data?.content) {
      return data.data.content
    }
  } catch {}
  return `[读取文件失败: ${filepath}]`
}

function handleBeforeUnload() {
  if (!projectId.value) return
  const payload = {
    chat_messages: chatMessages.value.map(m => ({ role: m.role, content: m.content, started_at: m.started_at, ended_at: m.ended_at, isForm: m.isForm })),
    chat_round: chatRound.value,
    doc_content: docContent.value,
    current_phase: innerPhase.value,
    saved_doc_path: savedDocPath.value,
    extracted_docs: extractedDocs.value.map(d => ({ id: d.id, name: d.name, content: d.content, selected: d.selected })),
    doc_save_counter: docSaveCounter,
    uploaded_refs: refFiles.value.map(r => ({ name: r.name, path: r.path, size: r.size })),
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
  // 30秒后显示重试按钮
  setTimeout(() => {
    if (!questionnaireReady.value && !srsDone.value) showRetry.value = true
  }, 30000)

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

async function previewShard(shard: { key: string; path: string }) {
  shardPreviewTitle.value = shard.key
  shardPreviewContent.value = '加载中...'
  shardPreviewVisible.value = true
  try {
    const res = await workflowApi.readStep3File(projectId.value, shard.path) as any
    const data = res?.data || res
    shardPreviewContent.value = data?.content || '（空文件）'
  } catch (e: any) {
    shardPreviewContent.value = '读取失败: ' + (e.message || '未知错误')
  }
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

async function handleUploadFile(file: File): Promise<boolean> {
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.warning('文件大小不能超过10MB')
    return false
  }
  // 同名文件不重复上传
  if (refFiles.value.some(r => r.name === file.name)) {
    ElMessage.info(`"${file.name}" 已上传，跳过`)
    return false
  }
  try {
    const reader = new FileReader()
    const contentB64 = await new Promise<string>((resolve, reject) => {
      reader.onload = () => {
        const result = reader.result as string
        resolve(result.split(',')[1])
      }
      reader.onerror = reject
      reader.readAsDataURL(file)
    })

    const res = await workflowApi.uploadStep3Ref(projectId.value, file.name, contentB64) as any
    const uploadData = res?.data || res
    refFiles.value.push({ name: file.name, path: uploadData?.path || '', size: file.size })
    saveChatSession()
    ElMessage.success(`已上传参考文档: ${file.name}`)
  } catch (e: any) {
    ElMessage.error('上传文件失败: ' + (e.message || '未知错误'))
  }
  return false
}

async function retryQuestionnaire() {
  // 先查询后台数据库，确认问卷尚未提交
  try {
    const token = localStorage.getItem('access_token') || ''
    const resp = await fetch('/api/v1/workflow/' + projectId.value + '/step3/status', {
      headers: { 'Authorization': 'Bearer ' + token },
    })
    const json = await resp.json()
    const d = json && (json.data || json)
    if (d) {
      const submitted = d.srs_done || d.questionnaire_submitted || (d.chat_checkpoint && d.chat_checkpoint.answers_submitted) || (d.chat_messages && d.chat_messages.some(function(m) { return m.action === 'submit_answers' }))
      if (submitted) {
        questionnaireSubmitted.value = true
        ElMessage.warning('问卷已提交，不可重新生成')
        return
      }
    }
  } catch (_) {}
  if (questionnaireSubmitted.value) {
    ElMessage.warning('问卷已提交，不可重新生成')
    return
  }
  showRetry.value = false
  chatLoading.value = true
  questionnaireGenerating.value = true
  innerPhase.value = 'questionnaire'
  srsStreamContent.value = ''
  chatError.value = ''
  wsStatus.value = '连接中...'
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: 'generate_questionnaire' }))
  } else {
    pendingMessages = [JSON.stringify({ action: 'generate_questionnaire' })]
    connectWebSocket()
  }
}

function removeRefFile(index: number) {
  refFiles.value.splice(index, 1)
  saveChatSession()
}

function handleSendChat() {
  const text = chatInput.value.trim()
  if (!text || chatLoading.value) return
  chatInput.value = ''
  chatMessages.value.push({ role: 'user', content: text, started_at: nowStr(), ended_at: nowStr() })
  chatLoading.value = true

  const history = chatMessages.value.map(m => ({
    role: m.role === 'houxing' ? 'assistant' : m.role,
    content: m.content,
  }))
  const payload = JSON.stringify({ action: 'chat', message: text, history })
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(payload)
  } else {
    pendingMessages.push(payload)
    connectWebSocket()
  }
}

function handleSubmitAnswers() {
  // 保存当前题答案
  saveCurrentAnswer()

  // 检查是否全部作答
  const missing = allQids.value.filter(qid => !answers.value[qid])
  if (missing.length > 0) {
    ElMessage.warning(`还有 ${missing.length} 题未作答，请全部完成后再提交`)
    return
  }

  // 发送答案
  questionnaireSubmitted.value = true
  lastSubmittedAnswers.value = { ...answers.value }
  const answerSummary = `📋 已提交 ${Object.keys(answers.value).length} 道问卷答案`
  chatMessages.value.push({ role: 'user', content: answerSummary, started_at: nowStr() })
  chatMessages.value.push({ role: 'houxing', content: '🤖 正在通过子Agent生成SRS需求文档，请稍候...', started_at: nowStr() })
  const payload = JSON.stringify({ action: 'submit_answers', answers: answers.value })
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(payload)
    srsGenerating.value = true
    srsProgress.value = 0
    srsStreamContent.value = ''
    chatLoading.value = true
  } else {
    pendingMessages.push(payload)
    connectWebSocket()
    srsGenerating.value = true
    srsProgress.value = 0
    srsStreamContent.value = ''
    chatLoading.value = true
  }
}

function retrySrsGeneration() {
  const stored = lastSubmittedAnswers.value
  if (Object.keys(stored).length === 0) {
    ElMessage.warning('没有已提交的问卷答案，请重新填写问卷')
    return
  }

  // 移除旧的错误消息，显示正在重试
  chatMessages.value = chatMessages.value.filter(m => !m.isError)
  chatMessages.value.push({ role: 'houxing', content: '🤖 正在重新生成SRS需求文档，请稍候...', started_at: nowStr() })
  srsGenerating.value = true
  srsProgress.value = 0
  srsStreamContent.value = ''
  chatLoading.value = true
  chatError.value = ''

  const payload = JSON.stringify({ action: 'submit_answers', answers: stored })
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(payload)
  } else {
    pendingMessages.push(payload)
    connectWebSocket()
  }
}

async function handleRequestQA() {
  qaInProgress.value = true
  qaResult.value = null
  const payload = JSON.stringify({ action: 'request_qa' })
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(payload)
  } else {
    pendingMessages.push(payload)
    connectWebSocket()
  }
}

async function handleFinishDiscuss() {
  await saveChatSession()
  if (shardIndex.value.length > 0) {
    innerPhase.value = 'qa'
    return
  }
  ElMessage.info('请先完成问卷并等待SRS生成')
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
      router.push({ name: 'Step3Qa', params: { projectId: projectId.value } })
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
      innerPhase.value = 'qa'
    }
  } finally {
    submitting.value = false
  }
}


async function handleSubmitDocToQA() {
  if (shardIndex.value.length > 0) {
    docContent.value = shardIndexContent.value || 'SRS分片索引表（详见各分片文件）'
  }
  if (!docContent.value?.trim()) {
    ElMessage.warning('需求文档内容为空')
    return
  }
  await doSaveAndSubmit()
}

async function backToDiscuss() {
  innerPhase.value = 'srs_ready'
}

async function handleComplete() {
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

  &__chat-section { flex: 1; display: grid; grid-template-columns: 1000px 380px; gap: $spacing-4; min-height: 0; min-width: 0; justify-content: center; }
  &__chat-panel { width: 1000px; display: flex; flex-direction: column; background: $canvas; border-radius: $radius-lg; border: 1px solid $hairline; overflow: hidden; min-width: 0; }

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
    &-bubble { max-width: 80%; min-width: 0; padding: 10px 14px; border-radius: $radius-sm; font-family: $font-text; font-size: $body-size; line-height: $body-leading; letter-spacing: $body-tracking; white-space: pre-wrap; word-break: break-word; }
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

  &__submit-section, &__complete-section {
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

  &__qa-timer {
    display: flex; gap: $spacing-4; justify-content: center;
    margin-top: $spacing-sm; font-size: 13px; color: $ink-muted-48;
    span { white-space: nowrap; }
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
      border-color: $status-review;
      background: #fffbf0;
      box-shadow: 0 0 0 2px rgba($status-review, 0.1);
    }

    &--failed {
      border-color: $priority-urgent;
      background: #fef2f2;
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

  // 4子步骤进度条
  &__sub-step-progress {
    display: flex; align-items: center; justify-content: center; gap: 0;
    padding: $spacing-sm $spacing-8; margin-bottom: $spacing-4;
    background: $canvas-parchment; border: 1px solid $hairline; border-radius: $radius-lg;
    overflow-x: auto;
  }
  &__sub-step-item {
    display: flex; align-items: center; gap: $spacing-xs; padding: 0 $spacing-sm; position: relative; flex-shrink: 0;
    &::after {
      content: ''; position: absolute; right: -$spacing-xs; top: 50%;
      width: 8px; height: 8px; border-right: 2px solid $hairline; border-bottom: 2px solid $hairline;
      transform: translateY(-50%) rotate(-45deg);
    }
    &:last-child::after { display: none; }
    &--done {
      .step3-view__sub-step-indicator { background: $status-done; color: $on-primary; border-color: $status-done; }
      .step3-view__sub-step-label { color: $status-done; }
    }
    &--active {
      .step3-view__sub-step-indicator { background: $primary; color: $on-primary; border-color: $primary; box-shadow: 0 0 0 3px rgba($primary, 0.2); }
      .step3-view__sub-step-label { color: $primary; font-weight: 600; }
    }
    &--pending {
      .step3-view__sub-step-indicator { background: $canvas; color: $ink-muted-48; border-color: $hairline; }
      .step3-view__sub-step-label { color: $ink-muted-48; }
    }
  }
  &__sub-step-indicator {
    width: 28px; height: 28px; border-radius: 50%; border: 2px solid $hairline;
    display: flex; align-items: center; justify-content: center;
    font-size: $fine-print-size; font-weight: 600; flex-shrink: 0;
  }
  &__sub-step-label { font-size: $caption-size; white-space: nowrap; }

  // 问卷样式 - 严格隔离，固定700px，不影响外部布局
  &__form-wrap {
    width: 100%;
    max-width: 100%;
    overflow-x: auto;
    isolation: isolate;
  }
  &__form-content {
    width: 700px;
    max-width: 100%;
    box-sizing: border-box;
    :deep(.brain-q) {
      background: $canvas-parchment;
      border: 1px solid $hairline;
      border-radius: $radius-sm;
      padding: $spacing-sm $spacing-4;
      margin-bottom: $spacing-sm;
      box-sizing: border-box;

      .brain-q-title {
        font-size: $body-strong-size;
        font-weight: $body-strong-weight;
        color: $ink;
        margin: 0 0 $spacing-sm;
      }

      .brain-option {
        display: flex;
        align-items: center;
        gap: $spacing-xs;
        padding: $spacing-xs 0;
        font-size: $body-size;
        color: $ink;
        cursor: pointer;

        input[type="radio"] {
          accent-color: $primary;
          width: 16px;
          height: 16px;
          flex-shrink: 0;
          cursor: pointer;
        }

        &:hover { color: $primary; }
      }
    }
  }

  // 问卷提交按钮（显示在对话框底部）
  &__questionnaire-actions {
    padding: $spacing-sm $spacing-4;
    border-top: 1px solid $hairline;
    text-align: center;
    background: $canvas;
  }

  &__question-indicator {
    text-align: center;
    padding: $spacing-xs 0;
    font-size: $caption-size;
    color: $ink-muted-48;
    border-bottom: 1px solid $hairline;
    background: $hairline;
  }

  &__question-nav {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: $spacing-sm;
  }

  &__question-counter {
    font-size: $body-size;
    color: $ink-muted-48;
    min-width: 60px;
    text-align: center;
  }

  &__srs-stream {
    max-height: 400px;
    overflow-y: auto;
    background: $canvas;
    border: 1px solid $hairline;
    border-radius: $radius-sm;
    padding: $spacing-sm;
    margin-top: $spacing-sm;
    pre {
      margin: 0;
      font-family: monospace;
      font-size: $fine-print-size;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
      color: $ink;
    }
  }

  // 分片索引表样式
  &__shard-index {
    text-align: left;
    margin: $spacing-sm 0;

    &-header {
      font-size: $body-strong-size;
      font-weight: $body-strong-weight;
      color: $ink;
      margin-bottom: $spacing-sm;
      padding: $spacing-sm;
      background: $canvas-parchment;
      border-radius: $radius-sm;
      border: 1px solid $hairline;
    }

    &-table {
      border: 1px solid $hairline;
      border-radius: $radius-sm;
      overflow: hidden;
      margin-bottom: $spacing-sm;
    }

    &-row {
      display: flex;
      align-items: center;
      padding: $spacing-xs $spacing-sm;
      font-size: $caption-size;
      border-bottom: 1px solid $hairline;
      &:last-child { border-bottom: none; }
      &:hover { background: rgba($primary, 0.03); }

      &--header {
        background: $canvas-parchment;
        font-weight: 600;
        color: $ink-muted-48;
        &:hover { background: $canvas-parchment; }
      }
    }

    &-col-idx { width: 32px; flex-shrink: 0; color: $ink-muted-48; }
    &-col-path { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: monospace; font-size: $fine-print-size;
      &--clickable { color: var(--el-color-primary); text-decoration: underline; }
    }

    &-preview {
      pre {
        font-family: monospace;
        font-size: $fine-print-size;
        line-height: 1.5;
        white-space: pre-wrap;
        word-break: break-word;
        background: $canvas-parchment;
        padding: $spacing-sm;
        border-radius: $radius-sm;
        border: 1px solid $hairline;
        max-height: 200px;
        overflow-y: auto;
        margin: 0;
      }
    }
  }
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
  flex-shrink: 0;
  padding: $spacing-sm $spacing-4;
  border-top: 1px solid $hairline;
  background: $canvas;

  &__refs {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-xs;
    margin-bottom: $spacing-xs;
  }

  &__row {
    display: flex;
    gap: $spacing-xs;
    align-items: flex-end;
  }

  &__upload-btn {
    height: 56px;
    width: 40px;
    padding: 0 !important;
    font-size: 18px;
  }

  .step3-view__send-btn {
    flex-shrink: 0;
    height: 56px;
  }
}
</style>
