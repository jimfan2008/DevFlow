<template>
  <div class="agent-detail-view" v-loading="store.loading">
    <!-- Header -->
    <div class="agent-detail-view__header">
      <el-button :icon="ArrowLeft" text @click="router.push({ name: 'AgentList' })">返回</el-button>
      <div class="agent-detail-view__header-info">
        <h2>{{ store.currentAgent?.name }}</h2>
        <el-tag v-if="store.currentAgent" :type="statusTagType" effect="dark" size="small">
          {{ statusText }}
        </el-tag>
        <el-tag v-if="store.currentAgent?.agent_type === 'hermes'" type="" size="small" effect="plain">Hermes</el-tag>
        <span v-if="store.currentAgent?.version" class="agent-detail-view__version">v{{ store.currentAgent.version }}</span>
      </div>
      <div class="agent-detail-view__header-actions">
        <el-button size="small" @click="handleRefresh">刷新</el-button>
      </div>
    </div>

    <template v-if="store.currentAgent">
      <el-row :gutter="16" class="agent-detail-view__body">
        <!-- Left: Config Panel -->
        <el-col :span="12">
          <el-card shadow="never" class="agent-detail-view__card">
            <template #header>
              <div class="agent-detail-view__card-title">
                <span>配置信息</span>
              </div>
            </template>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="Agent类型">
                <el-tag size="small" :type="store.currentAgent.agent_type === 'hermes' ? '' : 'success'">
                  {{ store.currentAgent.agent_type === 'hermes' ? 'Hermes Agent' : '编程Agent' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="运行状态">
                <el-tag :type="statusTagType" size="small" effect="dark">{{ statusText }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="API端点">{{ store.currentAgent.api_endpoint || '-' }}</el-descriptions-item>
              <el-descriptions-item label="Gateway端口">{{ gatewayPort || '-' }}</el-descriptions-item>
              <el-descriptions-item label="连接模式">{{ connectionMode }}</el-descriptions-item>
              <el-descriptions-item label="版本">{{ store.currentAgent.version || '-' }}</el-descriptions-item>
              <el-descriptions-item label="发现者">{{ store.currentAgent.discovered_by || '-' }}</el-descriptions-item>
              <el-descriptions-item label="最后心跳">{{ store.currentAgent.last_heartbeat_at ? formatTime(store.currentAgent.last_heartbeat_at) : '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card shadow="never" class="agent-detail-view__card">
            <template #header>技能列表</template>
            <div v-if="store.currentAgent.capabilities?.length">
              <el-tag v-for="cap in store.currentAgent.capabilities" :key="cap" style="margin: 4px">{{ cap }}</el-tag>
            </div>
            <div v-else-if="store.currentAgent.agent_type === 'hermes'" class="agent-detail-view__no-skills">
              <el-empty description="暂无技能" :image-size="60">
                <el-button size="small" @click="handleSkillDiscovery">触发Skill发现</el-button>
              </el-empty>
            </div>
            <el-empty v-else description="暂无技能" :image-size="60" />
          </el-card>
        </el-col>

        <!-- Right: Chat Panel -->
        <el-col :span="12">
          <el-card shadow="never" class="agent-detail-view__chat-card">
            <template #header>
              <div class="agent-detail-view__card-title">
                <span>
                  <span class="agent-detail-view__hermes-icon">🤖</span>
                  与 {{ store.currentAgent.name }} 对话
                </span>
                <el-tag v-if="store.currentAgent.agent_type === 'hermes'" size="small" type="success" effect="dark" style="margin-left: 8px;">实时连接</el-tag>
                <el-tag v-else size="small" type="info">离线模式</el-tag>
              </div>
            </template>

            <div class="agent-detail-view__chat" ref="chatRef">
              <div v-if="messages.length === 0" class="agent-detail-view__chat-empty">
                <div class="agent-detail-view__chat-welcome">
                  <div class="agent-detail-view__chat-avatar">🤖</div>
                  <p>与 {{ store.currentAgent.name }} 直接对话</p>
                  <p class="agent-detail-view__chat-sub">向 Hermes Agent 发送消息，它将实时回复你。</p>
                </div>
                <div class="agent-detail-view__chat-starters">
                  <el-button
                    v-for="s in starters"
                    :key="s"
                    size="small"
                    @click="handleStarterClick(s)"
                    :disabled="chatLoading"
                    class="agent-detail-view__starter-btn"
                  >
                    {{ s }}
                  </el-button>
                </div>
              </div>

              <div
                v-for="(msg, idx) in messages"
                :key="idx"
                :class="['agent-detail-view__chat-msg', msg.role]"
              >
                <div class="agent-detail-view__chat-avatar-small">
                  {{ msg.role === 'hermes' ? '🤖' : '👤' }}
                </div>
                <div class="agent-detail-view__chat-bubble">{{ msg.content }}</div>
              </div>

              <div v-if="chatLoading" class="agent-detail-view__chat-msg hermes">
                <div class="agent-detail-view__chat-avatar-small">🤖</div>
                <div class="agent-detail-view__chat-bubble hermes-thinking">
                  <span class="dot-pulse">思考中<span>.</span><span>.</span><span>.</span></span>
                </div>
              </div>
            </div>

            <div class="agent-detail-view__chat-input">
              <el-input
                v-model="chatInput"
                type="textarea"
                :rows="2"
                placeholder="输入消息与 Hermes 对话..."
                :disabled="chatLoading"
                @keyup.enter.ctrl="handleChatSend"
              />
              <el-button
                type="primary"
                size="large"
                :loading="chatLoading"
                :disabled="!chatInput.trim()"
                @click="handleChatSend"
                class="agent-detail-view__chat-send-btn"
              >
                <el-icon><Promotion /></el-icon>
                发送
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <div class="agent-detail-view__footer-actions">
        <el-button v-if="store.currentAgent.agent_type === 'hermes'" type="primary" plain @click="handleSkillDiscovery">触发Skill发现</el-button>
        <el-button type="danger" plain @click="handleDelete">移除Agent</el-button>
      </div>
    </template>

    <!-- Error state -->
    <el-result v-else-if="store.error" icon="error" :title="store.error" sub-title="无法加载Agent详情">
      <template #extra>
        <el-button @click="router.push({ name: 'AgentList' })">返回列表</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Promotion } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAgentStore } from '@/stores/useAgentStore'
import { agentApi } from '@/api'

const router = useRouter()
const route = useRoute()
const store = useAgentStore()

const messages = ref<{ role: string; content: string }[]>([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatRef = ref<HTMLElement | null>(null)

const starters = [
  '你好，Hermes！',
  '你能做什么？',
  '帮我分析一个项目需求',
  '介绍一下你自己',
]

const statusTagType = computed(() => {
  const status = store.currentAgent?.status
  if (status === 'online') return 'success'
  if (status === 'busy') return 'warning'
  return 'info'
})

const statusText = computed(() => {
  const status = store.currentAgent?.status
  if (status === 'online') return '在线'
  if (status === 'busy') return '忙碌'
  return '离线'
})

const gatewayPort = computed(() => {
  return store.currentAgent?.config?.gateway_port || '-'
})

const connectionMode = computed(() => {
  const config = store.currentAgent?.config || {}
  if (config.gateway_port) return 'HTTP Gateway'
  if (config.use_cli) return 'CLI 模式'
  return '未配置'
})

onMounted(() => {
  const agentId = route.params.agentId as string
  store.fetchAgentDetail(agentId)
})

async function handleChatSend() {
  const text = chatInput.value.trim()
  if (!text || chatLoading.value) return
  const agentId = route.params.agentId as string
  if (!agentId) return

  chatInput.value = ''
  messages.value.push({ role: 'user', content: text })
  chatLoading.value = true
  scrollToBottom()

  try {
    const res = await agentApi.chat(agentId, text) as any
    const reply = res?.data?.reply
    if (reply) {
      messages.value.push({ role: 'hermes', content: reply })
    }
  } catch (e: any) {
    messages.value.push({ role: 'hermes', content: '与 Hermes 通信失败，请稍后重试。' })
  } finally {
    chatLoading.value = false
    scrollToBottom()
  }
}

function handleStarterClick(s: string) {
  chatInput.value = s
  handleChatSend()
}

async function handleSkillDiscovery() {
  if (!store.currentAgent) return
  const result = await store.triggerSkillDiscovery(store.currentAgent.id)
  if (result) ElMessage.success('Skill发现完成')
}

async function handleDelete() {
  if (!store.currentAgent) return
  try {
    await ElMessageBox.confirm('确定移除该Agent？', '确认', { type: 'warning' })
    await store.deleteAgent(store.currentAgent.id)
    ElMessage.success('Agent已移除')
    router.push({ name: 'AgentList' })
  } catch {}
}

async function handleRefresh() {
  const agentId = route.params.agentId as string
  if (agentId) {
    await store.fetchAgentDetail(agentId)
  }
}

function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN')
}

function scrollToBottom() {
  nextTick(() => {
    if (chatRef.value) {
      chatRef.value.scrollTop = chatRef.value.scrollHeight
    }
  })
}

watch(() => messages.value.length, () => scrollToBottom())
</script>

<style lang="scss" scoped>
.agent-detail-view {
  padding: 24px;
  height: 100%;
  overflow-y: auto;

  &__header {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    margin-bottom: $spacing-5;

    &-info {
      flex: 1;
      display: flex;
      align-items: center;
      gap: $spacing-xs;
      h2 {
        margin: 0;
        font-family: $font-display;
        font-size: $display-lg-size;
        font-weight: $display-lg-weight;
        line-height: $display-lg-leading;
        letter-spacing: $display-lg-tracking;
        color: $ink;
      }
    }

    &-actions {
      display: flex;
      gap: $spacing-xs;
    }
  }

  &__version {
    font-size: $fine-print-size;
    color: $ink-muted-48;
  }

  &__body {
    margin-bottom: $spacing-4;
  }

  &__card {
    margin-bottom: $spacing-4;
    border-radius: $radius-lg;
  }

  &__card-title {
    display: flex;
    align-items: center;
    font-family: $font-text;
    font-weight: $body-strong-weight;
    font-size: $body-strong-size;
    letter-spacing: $body-strong-tracking;
  }

  &__hermes-icon {
    margin-right: $spacing-xxs;
  }

  &__no-skills {
    padding: $spacing-xs 0;
  }

  // ── Chat Panel ──────────────────────────
  &__chat-card {
    height: calc(100vh - 200px);
    display: flex;
    flex-direction: column;
    border-radius: $radius-lg;
    :deep(.el-card__body) {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 0;
      overflow: hidden;
    }
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
      gap: $spacing-4;
    }

    &-welcome {
      text-align: center;
      p { margin: $spacing-xxs 0; font-size: $body-size; }
    }

    &-sub { color: $ink-muted-48; font-size: $caption-size !important; }
    &-avatar { font-size: 48px; }

    &-starters {
      display: flex;
      flex-wrap: wrap;
      gap: $spacing-xs;
      justify-content: center;
    }

    &-avatar-small {
      font-size: $spacing-lg;
      flex-shrink: 0;
    }

    &-msg {
      display: flex;
      gap: $spacing-xs;
      align-items: flex-start;

      &.user {
        flex-direction: row-reverse;
        .agent-detail-view__chat-bubble {
          background: $primary;
          color: $on-primary;
          border-bottom-right-radius: $radius-xs;
        }
      }

      &.hermes {
        .agent-detail-view__chat-bubble {
          background: $canvas;
          color: $ink;
          border: 1px solid $hairline;
          border-bottom-left-radius: $radius-xs;
        }
      }
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

      &.hermes-thinking {
        color: $ink-muted-48;
      }
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

  &__chat-send-btn {
    flex-shrink: 0;
    height: 56px;
  }

  &__footer-actions {
    display: flex;
    gap: 8px;
    padding: 8px 0;
  }
}

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