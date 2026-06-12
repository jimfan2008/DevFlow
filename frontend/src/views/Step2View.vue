<template>
  <div class="step2-view" v-loading="store.loading && store.phase !== 'organizing'">
    <!-- Header -->
    <div class="step2-view__header">
      <div class="step2-view__header-left">
        <el-button :icon="ArrowLeft" text @click="goBack">返回</el-button>
        <div>
          <h1>第二步：确认核心目标与搭建组织架构</h1>
          <p class="step2-view__subtitle">{{ store.projectName }} · 海梅主动对话</p>
        </div>
      </div>
      <div class="step2-view__header-right">
        <el-tag :type="phaseTagType" effect="dark" size="large">{{ phaseLabel }}</el-tag>
      </div>
    </div>

    <!-- Phase Progress -->
    <div class="step2-view__progress">
      <div
        v-for="(p, i) in phases"
        :key="p.key"
        class="step2-view__progress-step"
        :class="{
          'step2-view__progress-step--active': p.key === store.phase,
          'step2-view__progress-step--done': phaseIndex > i,
        }"
      >
        <div class="step2-view__progress-indicator">
          <span v-if="phaseIndex > i">✓</span>
          <span v-else>{{ i + 1 }}</span>
        </div>
        <div class="step2-view__progress-label">{{ p.label }}</div>
      </div>
    </div>

    <el-alert v-if="store.error" :title="store.error" type="error" show-icon closable class="step2-view__alert" />

    <!-- Phase: Chat (intro / chatting / confirming) -->
    <div v-if="isChatPhase" class="step2-view__chat-section">
      <div class="step2-view__chat-panel">
        <div class="step2-view__panel-header">
          <h3>
            <span class="step2-view__haimei-icon">🌊</span>
            海梅（HaiMei）· 项目经理
          </h3>
          <div class="step2-view__panel-actions">
            <span class="step2-view__round-count" v-if="store.messages.length > 0">第 {{ store.chatRound }} 轮对话</span>
          </div>
        </div>

        <div class="step2-view__chat" ref="chatRef">
          <div v-if="store.messages.length === 0" class="step2-view__chat-empty">
            <div class="step2-view__empty-icon">🌊</div>
            <p>海梅正在等待与您对话...</p>
          </div>

          <div
            v-for="(msg, idx) in store.messages"
            :key="idx"
            :class="['step2-view__chat-msg', msg.role]"
          >
            <div class="step2-view__chat-avatar">
              {{ msg.role === 'haimei' ? '🌊' : msg.role === 'system' ? '⚙️' : '👤' }}
            </div>
            <div class="step2-view__chat-bubble" v-html="renderContent(msg.content)"></div>
          </div>

          <div v-if="store.loading && isChatPhase" class="step2-view__chat-msg haimei">
            <div class="step2-view__chat-avatar">🌊</div>
            <div class="step2-view__chat-bubble step2-view__chat-thinking">
              <span class="dot-pulse">思考中<span>.</span><span>.</span><span>.</span></span>
            </div>
          </div>
        </div>

        <div class="step2-view__chat-input">
          <el-input
            v-model="chatInput"
            type="textarea"
            :rows="2"
            :placeholder="chatPlaceholder"
            :disabled="store.loading"
            @keyup.enter.ctrl="handleSend"
          />
          <el-button
            v-if="store.phase !== 'confirming'"
            type="primary"
            size="large"
            :loading="store.loading"
            :disabled="!chatInput.trim()"
            @click="handleSend"
            class="step2-view__send-btn"
          >
            <el-icon><Promotion /></el-icon>
            发送
          </el-button>
          <el-button
            v-else
            type="success"
            size="large"
            :loading="store.loading"
            :disabled="!chatInput.trim()"
            @click="handleConfirmGoal"
            class="step2-view__send-btn"
          >
            确认核心目标 ✅
          </el-button>
        </div>
      </div>

      <div class="step2-view__goal-panel">
        <div class="step2-view__panel-header">
          <h3>
            <span class="step2-view__goal-icon">🎯</span>
            核心目标
          </h3>
          <el-tag v-if="store.confirmedGoal" type="success" size="small" effect="dark">已确认</el-tag>
          <el-tag v-else-if="store.coreGoal" type="warning" size="small">待确认</el-tag>
          <el-tag v-else type="info" size="small">未定义</el-tag>
        </div>

        <div class="step2-view__goal-editor">
          <el-input
            v-model="goalEdit"
            type="textarea"
            :rows="6"
            placeholder="项目的核心目标将在这里呈现..."
            :disabled="store.phase !== 'chatting' && store.phase !== 'confirming'"
          />
        </div>

        <div class="step2-view__goal-actions">
          <el-button
            v-if="store.phase === 'confirming' || store.phase === 'chatting'"
            type="primary"
            :disabled="!goalEdit.trim() || !!store.confirmedGoal"
            @click="handleDirectConfirm"
            size="large"
            class="step2-view__action-btn"
          >
            确认核心目标
          </el-button>
        </div>
      </div>
    </div>

    <!-- Phase: Organizing -->
    <div v-if="store.phase === 'organizing'" class="step2-view__org-section">
      <div class="step2-view__org-header">
        <h2>🏗️ 项目组织架构</h2>
        <p class="step2-view__org-subtitle">海梅正在激活以下 9 个 Agent 角色...</p>
        <div class="step2-view__org-progress">
          <el-progress
            :percentage="Math.round((store.agents.filter(a => a.activated).length / 9) * 100)"
            :stroke-width="8"
            :text-inside="false"
            status="success"
          />
          <span class="step2-view__org-count">{{ store.currentAgentStatus }} 已激活</span>
        </div>
      </div>

      <div class="step2-view__org-grid">
        <div
          v-for="agent in store.agents"
          :key="agent.name"
          class="step2-view__org-card"
          :class="{ 'step2-view__org-card--activated': agent.activated }"
        >
          <div class="step2-view__org-card-icon">{{ agentIcons[agent.name] || '🤖' }}</div>
          <div class="step2-view__org-card-info">
            <div class="step2-view__org-card-name">
              {{ agent.chineseName }}
              <span class="step2-view__org-card-en">({{ agent.name }})</span>
            </div>
            <div class="step2-view__org-card-role">{{ agent.role }}</div>
            <div class="step2-view__org-card-desc">{{ agent.responsibility }}</div>
          </div>
          <div class="step2-view__org-card-status">
            <el-tag v-if="agent.activated" type="success" size="small" effect="dark">已激活</el-tag>
            <el-tag v-else type="info" size="small" effect="plain">待激活</el-tag>
          </div>
        </div>
      </div>

      <div v-if="store.agents.every(a => a.activated)" class="step2-view__org-done">
        <el-alert title="所有Agent角色已激活！正在创建讨论群..." type="success" show-icon :closable="false" />
      </div>
    </div>

    <!-- Phase: Grouping -->
    <div v-if="store.phase === 'grouping'" class="step2-view__group-section">
      <div class="step2-view__group-card">
        <div class="step2-view__group-icon">💬</div>
        <h2>创建项目讨论群</h2>
        <p>正在创建讨论群并将所有Agent加入群组...</p>
        <el-progress :percentage="groupProgress" :stroke-width="6" status="success" />
        <div v-if="store.groupInfo" class="step2-view__group-result">
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="群组名称">{{ store.groupInfo.name }}</el-descriptions-item>
            <el-descriptions-item label="模式">
              <el-tag size="small" type="primary">讨论模式</el-tag>
              <el-tag size="small" type="success" style="margin-left: 4px">会议模式</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="成员数量">{{ store.groupInfo.members?.length || 0 }} 人</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(store.groupInfo.created_at) }}</el-descriptions-item>
          </el-descriptions>
          <div class="step2-view__group-members">
            <el-tag
              v-for="m in store.groupInfo.members"
              :key="m.id || m"
              size="small"
              type="info"
              effect="plain"
              style="margin: 2px"
            >
              {{ m.display_name || m.username || m }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- Phase: QA -->
    <div v-if="store.phase === 'qa'" class="step2-view__qa-section">
      <div class="step2-view__qa-card">
        <div class="step2-view__qa-header">
          <div class="step2-view__qa-icon">🔍</div>
          <h2>后荣（HouRong）· QA 检验</h2>
        </div>
        <p class="step2-view__qa-subtitle">检验第二步的产出是否达到验收标准</p>

        <div v-if="store.qaPassed" class="step2-view__qa-result step2-view__qa-result--passed">
          <el-result icon="success" title="QA检验通过" :sub-title="store.qaMessage">
            <template #extra>
              <el-button type="primary" @click="handleComplete">进入下一步 ➜</el-button>
            </template>
          </el-result>
        </div>
        <div v-else class="step2-view__qa-result step2-view__qa-result--failed">
          <el-result icon="error" title="QA检验未通过" :sub-title="store.qaMessage">
            <template #extra>
              <el-button type="primary" @click="handleRetryQA">重新检验</el-button>
            </template>
          </el-result>
        </div>
      </div>
    </div>

    <!-- Phase: Complete -->
    <div v-if="store.phase === 'complete'" class="step2-view__complete-section">
      <div class="step2-view__complete-card">
        <div class="step2-view__complete-icon">🎉</div>
        <h2>第二步完成！</h2>
        <p class="step2-view__complete-subtitle">核心目标确认与组织架构搭建已全部完成</p>

        <el-divider />

        <div class="step2-view__complete-summary">
          <div class="step2-view__complete-item">
            <div class="step2-view__complete-item-icon">🎯</div>
            <div class="step2-view__complete-item-content">
              <div class="step2-view__complete-item-label">核心目标</div>
              <div class="step2-view__complete-item-value">{{ store.confirmedGoal }}</div>
            </div>
            <el-tag type="success" size="small" effect="dark">已确认</el-tag>
          </div>
          <div class="step2-view__complete-item">
            <div class="step2-view__complete-item-icon">🏗️</div>
            <div class="step2-view__complete-item-content">
              <div class="step2-view__complete-item-label">组织架构</div>
              <div class="step2-view__complete-item-value">9个Agent角色已全部激活</div>
            </div>
            <el-tag type="success" size="small" effect="dark">已完成</el-tag>
          </div>
          <div class="step2-view__complete-item">
            <div class="step2-view__complete-item-icon">💬</div>
            <div class="step2-view__complete-item-content">
              <div class="step2-view__complete-item-label">讨论群</div>
              <div class="step2-view__complete-item-value">{{ store.groupInfo?.name || '项目讨论群' }}</div>
            </div>
            <el-tag type="success" size="small" effect="dark">已建立</el-tag>
          </div>
        </div>

        <el-divider />

        <div class="step2-view__complete-actions">
          <el-button size="large" @click="goBack">返回项目</el-button>
          <el-button type="primary" size="large" :loading="store.loading" @click="handleComplete">
            完成并进入下一步 ➜
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Promotion } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useStep2Store } from '@/stores/useStep2Store'

const router = useRouter()
const route = useRoute()
const store = useStep2Store()

const chatInput = ref('')
const goalEdit = ref('')
const chatRef = ref<HTMLElement | null>(null)
const groupProgress = ref(0)

const agentIcons: Record<string, string> = {
  HaiMei: '🌊',
  HouXing: '📋',
  HouWang: '🏗️',
  HouFa: '💻',
  HouDa: '🧪',
  HouFu: '🚀',
  HouGui: '📄',
  HouRong: '🔍',
  HouHua: '🔒',
}

const phases = [
  { key: 'intro', label: '海梅对话' },
  { key: 'chatting', label: '沟通确认' },
  { key: 'confirming', label: '确认目标' },
  { key: 'organizing', label: '搭建架构' },
  { key: 'grouping', label: '创建群组' },
  { key: 'qa', label: 'QA检验' },
  { key: 'complete', label: '完成' },
] as const

const phaseIndex = computed(() => {
  const idx = phases.findIndex(p => p.key === store.phase)
  return idx >= 0 ? idx : 0
})

const phaseLabel = computed(() => {
  const p = phases.find(p => p.key === store.phase)
  return p?.label || store.phase
})

const phaseTagType = computed(() => {
  const map: Record<string, string> = {
    intro: 'info',
    chatting: 'primary',
    confirming: 'warning',
    organizing: 'warning',
    grouping: 'warning',
    qa: 'warning',
    complete: 'success',
  }
  return map[store.phase] || 'info'
})

const isChatPhase = computed(() =>
  ['intro', 'chatting', 'confirming'].includes(store.phase)
)

const chatPlaceholder = computed(() => {
  if (store.phase === 'intro' || store.phase === 'chatting') {
    return '描述你的项目想法，海梅将帮你梳理核心目标...'
  }
  if (store.phase === 'confirming') {
    return '回复"确认"锁定核心目标，或输入修改意见...'
  }
  return ''
})

onMounted(async () => {
  const pid = route.params.projectId as string
  const pname = route.query.name as string || '未命名项目'
  if (!pid) {
    ElMessage.error('缺少项目ID')
    router.push({ name: 'ProjectList' })
    return
  }
  store.reset(pid, pname)
  goalEdit.value = ''

  // 尝试从后端恢复已保存的状态
  const restored = await store.loadFromBackend(pid)
  if (restored) {
    goalEdit.value = store.coreGoal
    // 如果已经完成，滚到完成阶段
  } else {
    setTimeout(() => {
      store.startConversation()
    }, 300)
  }
})

watch(() => store.coreGoal, (val) => {
  if (val && !goalEdit.value) {
    goalEdit.value = val
  }
})

watch(() => store.messages.length, () => scrollToBottom())

watch(() => store.phase, (phase) => {
  if (phase === 'confirming') {
    goalEdit.value = store.coreGoal
  }
  if (phase === 'organizing') {
    store.activateAgents()
  }
  if (phase === 'grouping') {
    let progress = 0
    const interval = setInterval(() => {
      progress += Math.random() * 15 + 5
      if (progress >= 95) {
        progress = 95
        clearInterval(interval)
      }
      groupProgress.value = Math.min(Math.round(progress), 100)
    }, 300)
  }
})

function renderContent(text: string) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function scrollToBottom() {
  setTimeout(() => {
    if (chatRef.value) {
      chatRef.value.scrollTop = chatRef.value.scrollHeight
    }
  }, 100)
}

async function handleSend() {
  const text = chatInput.value.trim()
  if (!text || store.loading.value) return
  chatInput.value = ''
  await store.sendMessage(text)
}

function handleConfirmGoal() {
  const text = '确认'
  chatInput.value = ''
  store.sendMessage(text)
}

function handleDirectConfirm() {
  if (!goalEdit.value.trim()) return
  store.confirmGoalDirectly(goalEdit.value.trim())
}

function goBack() {
  if (store.projectId) {
    router.push({ name: 'ProjectDetail', params: { projectId: store.projectId } })
  } else {
    router.push({ name: 'ProjectList' })
  }
}

async function handleComplete() {
  store.loading = true
  try {
    await store.saveToBackend()
    const res = await store.completeStep()
    if (res) {
      await store.executeStep3()
      ElMessage.success('第二步完成！即将进入需求分析阶段')
      router.push({ name: 'Step3', params: { projectId: store.projectId } })
    }
  } finally {
    store.loading = false
  }
}

function handleRetryQA() {
  store.runQACheck()
}

function formatTime(t?: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}
</script>

<style scoped lang="scss">
.step2-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: $spacing-sm;

    &-left {
      display: flex;
      align-items: flex-start;
      gap: $spacing-sm;
      h1 {
        margin: 0;
        font-family: $font-display;
        font-size: $display-md-size;
        font-weight: $display-lg-weight;
        line-height: $display-lg-leading;
        color: $ink;
      }
    }

    &-right {
      flex-shrink: 0;
    }
  }

  &__subtitle {
    margin: $spacing-xxs 0 0;
    font-size: $caption-size;
    color: $ink-muted-48;
  }

  &__alert {
    margin-bottom: $spacing-sm;
  }

  // ── Progress bar ─────────────────────────────
  &__progress {
    display: flex;
    align-items: center;
    gap: 0;
    margin-bottom: $spacing-4;
    padding: $spacing-sm $spacing-4;
    background: $canvas;
    border: 1px solid $hairline;
    border-radius: $radius-lg;
    overflow-x: auto;

    &-step {
      display: flex;
      align-items: center;
      gap: $spacing-xs;
      padding: 0 $spacing-sm;
      position: relative;
      flex-shrink: 0;

      &::after {
        content: '';
        position: absolute;
        right: -$spacing-xs;
        top: 50%;
        width: 8px;
        height: 8px;
        border-right: 2px solid $hairline;
        border-bottom: 2px solid $hairline;
        transform: translateY(-50%) rotate(-45deg);
      }

      &:last-child::after {
        display: none;
      }

      &--done {
        .step2-view__progress-indicator {
          background: $status-done;
          color: $on-primary;
          border-color: $status-done;
        }
        .step2-view__progress-label {
          color: $status-done;
        }
      }

      &--active {
        .step2-view__progress-indicator {
          background: $primary;
          color: $on-primary;
          border-color: $primary;
        }
        .step2-view__progress-label {
          color: $primary;
          font-weight: 600;
        }
      }
    }

    &-indicator {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      border: 2px solid $hairline;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: $fine-print-size;
      font-weight: 600;
      color: $ink-muted-48;
      flex-shrink: 0;
    }

    &-label {
      font-size: $caption-size;
      color: $ink-muted-48;
      white-space: nowrap;
    }
  }

  // ── Chat Section (intro / chatting / confirming) ─
  &__chat-section {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: $spacing-4;
    min-height: 0;
  }

  &__chat-panel {
    display: flex;
    flex-direction: column;
    background: $canvas;
    border-radius: $radius-lg;
    border: 1px solid $hairline;
    overflow: hidden;
  }

  &__panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: $spacing-sm $spacing-4;
    border-bottom: 1px solid $hairline;
    h3 {
      margin: 0;
      font-family: $font-text;
      font-size: $body-strong-size;
      font-weight: $body-strong-weight;
      display: flex;
      align-items: center;
      gap: $spacing-xxs;
    }
  }

  &__panel-actions {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
  }

  &__round-count {
    font-size: $fine-print-size;
    color: $ink-muted-48;
    background: $canvas-parchment;
    padding: 2px 8px;
    border-radius: $radius-pill;
  }

  &__haimei-icon, &__goal-icon {
    font-size: 18px;
  }

  &__chat {
    flex: 1;
    overflow-y: auto;
    padding: $spacing-4;
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
    background: $canvas-parchment;

    &-empty {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: $spacing-sm;
      color: $ink-muted-48;
    }

    &-msg {
      display: flex;
      gap: $spacing-xs;
      align-items: flex-start;

      &.user {
        flex-direction: row-reverse;
        .step2-view__chat-bubble {
          background: $primary;
          color: $on-primary;
          border-bottom-right-radius: $radius-xs;
        }
      }

      &.haimei {
        .step2-view__chat-bubble {
          background: $canvas;
          color: $ink;
          border: 1px solid $hairline;
          border-bottom-left-radius: $radius-xs;
        }
      }

      &.system {
        .step2-view__chat-bubble {
          background: transparent;
          color: $ink-muted-48;
          font-size: $caption-size;
          border: none;
          padding: 4px 0;
        }
        .step2-view__chat-avatar {
          opacity: 0.5;
        }
      }
    }

    &-avatar {
      font-size: $spacing-lg;
      flex-shrink: 0;
    }

    &-bubble {
      max-width: 80%;
      padding: 10px 14px;
      border-radius: $radius-sm;
      font-family: $font-text;
      font-size: $body-size;
      line-height: $body-leading;
      letter-spacing: $body-tracking;
      white-space: pre-wrap;
      word-break: break-word;
    }

    &-thinking {
      color: $ink-muted-48;
    }
  }

  &__chat-input {
    display: flex;
    gap: $spacing-xs;
    padding: $spacing-sm $spacing-4;
    border-top: 1px solid $hairline;
    align-items: flex-end;
    background: $canvas;
  }

  &__send-btn {
    flex-shrink: 0;
    height: 56px;
  }

  // ── Goal Panel ───────────────────────────────
  &__goal-panel {
    display: flex;
    flex-direction: column;
    background: $canvas;
    border-radius: $radius-lg;
    border: 1px solid $hairline;
    overflow: hidden;
  }

  &__goal-editor {
    padding: $spacing-4;
    flex: 1;
    :deep(textarea) {
      font-family: $font-text;
      font-size: $body-size;
      line-height: $body-leading;
    }
  }

  &__goal-actions {
    padding: $spacing-sm $spacing-4;
    border-top: 1px solid $hairline;
  }

  &__action-btn {
    width: 100%;
    border-radius: $radius-pill !important;
  }

  // ── Empty State ──────────────────────────────
  &__empty-icon {
    font-size: 48px;
  }

  // ── Organizing Section ───────────────────────
  &__org-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: $spacing-4;
  }

  &__org-header {
    text-align: center;
    padding: $spacing-4 $spacing-4 0;
    h2 {
      margin: 0 0 $spacing-xs;
      font-family: $font-display;
      font-size: $display-md-size;
      font-weight: $display-lg-weight;
    }
  }

  &__org-subtitle {
    color: $ink-muted-48;
    margin: 0 0 $spacing-4;
    font-size: $body-size;
  }

  &__org-progress {
    max-width: 400px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }

  &__org-count {
    font-size: $caption-size;
    color: $ink-muted-48;
    white-space: nowrap;
  }

  &__org-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: $spacing-sm;
    padding: 0 $spacing-4 $spacing-4;
  }

  &__org-card {
    display: flex;
    gap: $spacing-sm;
    padding: $spacing-4;
    background: $canvas;
    border: 1px solid $hairline;
    border-radius: $radius-md;
    transition: all 0.3s ease;
    align-items: flex-start;

    &--activated {
      border-color: $status-done;
      background: linear-gradient(135deg, $canvas 0%, #f0fdf4 100%);
    }

    &-icon {
      font-size: 32px;
      flex-shrink: 0;
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: $canvas-parchment;
      border-radius: $radius-sm;
    }

    &-info {
      flex: 1;
      min-width: 0;
    }

    &-name {
      font-size: $body-strong-size;
      font-weight: $body-strong-weight;
      color: $ink;
      margin-bottom: 2px;
    }

    &-en {
      font-size: $caption-size;
      color: $ink-muted-48;
      font-weight: 400;
    }

    &-role {
      font-size: $caption-size;
      color: $primary;
      margin-bottom: 4px;
      font-weight: 500;
    }

    &-desc {
      font-size: $fine-print-size;
      color: $ink-muted-48;
      line-height: 1.4;
    }

    &-status {
      flex-shrink: 0;
    }
  }

  &__org-done {
    padding: 0 $spacing-4 $spacing-4;
    max-width: 500px;
    margin: 0 auto;
  }

  // ── Grouping Section ─────────────────────────
  &__group-section {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: $spacing-4;
  }

  &__group-card {
    max-width: 520px;
    width: 100%;
    padding: $spacing-8;
    background: $canvas;
    border: 1px solid $hairline;
    border-radius: $radius-lg;
    text-align: center;
    h2 {
      font-family: $font-display;
      font-size: $display-md-size;
      margin: 0 0 $spacing-xs;
    }
    p {
      color: $ink-muted-48;
      margin: 0 0 $spacing-4;
    }
  }

  &__group-icon {
    font-size: 48px;
    margin-bottom: $spacing-sm;
  }

  &__group-result {
    margin-top: $spacing-4;
    text-align: left;
  }

  &__group-members {
    margin-top: $spacing-sm;
    display: flex;
    flex-wrap: wrap;
  }

  // ── QA Section ───────────────────────────────
  &__qa-section {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: $spacing-4;
  }

  &__qa-card {
    max-width: 560px;
    width: 100%;
    padding: $spacing-8;
    background: $canvas;
    border: 1px solid $hairline;
    border-radius: $radius-lg;
    text-align: center;
  }

  &__qa-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: $spacing-xs;
    h2 {
      font-family: $font-display;
      font-size: $display-md-size;
      margin: 0;
    }
  }

  &__qa-icon {
    font-size: 36px;
  }

  &__qa-subtitle {
    color: $ink-muted-48;
    margin: $spacing-xs 0 $spacing-6;
  }

  &__qa-result {
    &--passed {
      :deep(.el-result__icon) {
        --el-result-icon-color: $status-done;
      }
    }
    &--failed {
      :deep(.el-result__icon) {
        --el-result-icon-color: $priority-urgent;
      }
    }
  }

  // ── Complete Section ─────────────────────────
  &__complete-section {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: $spacing-4;
  }

  &__complete-card {
    max-width: 600px;
    width: 100%;
    padding: $spacing-8;
    background: $canvas;
    border: 1px solid $hairline;
    border-radius: $radius-lg;
    text-align: center;
    h2 {
      font-family: $font-display;
      font-size: $display-lg-size;
      margin: 0 0 $spacing-xs;
      color: $status-done;
    }
  }

  &__complete-icon {
    font-size: 64px;
    margin-bottom: $spacing-sm;
  }

  &__complete-subtitle {
    color: $ink-muted-48;
    margin: 0 0 $spacing-4;
    font-size: $body-size;
  }

  &__complete-summary {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
    text-align: left;
  }

  &__complete-item {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-sm $spacing-4;
    background: $canvas-parchment;
    border-radius: $radius-sm;

    &-icon {
      font-size: 24px;
      flex-shrink: 0;
    }

    &-content {
      flex: 1;
      min-width: 0;
    }

    &-label {
      font-size: $caption-size;
      color: $ink-muted-48;
    }

    &-value {
      font-size: $body-size;
      color: $ink;
      font-weight: 500;
    }
  }

  &__complete-actions {
    display: flex;
    gap: $spacing-sm;
    justify-content: center;
  }
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
