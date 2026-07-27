<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
import type { StepStatus } from '@/composables/useWorkflowStep'

defineProps<{
  projectId: string
  stepNumber: number
  projectName: string
  loading: boolean
  executing: boolean
  error: string
  stepStatus: StepStatus
  stepName: string
  prevStep: number
  nextStep: number
  stageLog: { type: string; message: string }[]
  liveContent: string
  streamStatus: string
  haimeiPrompt: string
  showPrompt: boolean
  statusLabelMap: Record<string, string>
  statusTagType: Record<string, string>
}>()

const emit = defineEmits<{
  (e: 'execute'): void
  (e: 'go-prev'): void
  (e: 'go-next'): void
  (e: 'go-back'): void
  (e: 'toggle-prompt'): void
  (e: 'close-error'): void
}>()
</script>

<template>
<div class="workflow-step-view" v-loading="loading">
  <div class="workflow-step-view__header">
    <div class="workflow-step-view__header-left">
      <el-button :icon="ArrowLeft" text @click="emit('go-back')">返回</el-button>
      <div>
        <h1>步骤{{ stepNumber }}：{{ stepName }}</h1>
        <p class="workflow-step-view__subtitle">
          {{ projectName }}
          <el-tag :type="statusTagType[stepStatus] || 'info'" size="small" effect="dark" style="margin-left: 12px">
            {{ statusLabelMap[stepStatus] || stepStatus }}
          </el-tag>
        </p>
      </div>
    </div>
  </div>

  <el-alert v-if="error" :title="error" type="error" show-icon closable class="workflow-step-view__alert" @close="emit('close-error')" />

  <!-- pending -->
  <div v-if="stepStatus === 'pending'" class="workflow-step-view__card">
    <div class="workflow-step-view__card-icon">⏳</div>
    <h2>准备执行：{{ stepName }}</h2>
    <p>海梅将调度对应Agent执行此步骤。如果前置步骤已完成，点击"立即执行"即可启动。</p>
    <div class="workflow-step-view__action-row">
      <el-button type="primary" size="large" :loading="executing" @click="emit('execute')">
        🚀 立即执行
      </el-button>
      <el-button plain size="large" @click="emit('go-prev')">
        ← 回到步骤{{ prevStep }}
      </el-button>
    </div>
  </div>

  <!-- in_progress: slot for step-specific UI -->
  <div v-if="stepStatus === 'in_progress'" class="workflow-step-view__card workflow-step-view__card--executing">
    <slot name="in-progress">
      <div class="workflow-step-view__card-icon">⚙️</div>
      <h2>执行中...</h2>
      <p class="workflow-step-view__executing-status">{{ streamStatus || 'Agent 正在工作中...' }}</p>
      <el-progress :percentage="100" :stroke-width="4" status="warning" indeterminate style="max-width: 400px; margin: 16px auto" />
    </slot>
  </div>

  <!-- Haimei Prompt Display -->
  <div v-if="haimeiPrompt" class="workflow-step-view__card workflow-step-view__prompt-card">
    <div class="workflow-step-view__prompt-header" @click="emit('toggle-prompt')">
      <span>📝 海梅提示词</span>
      <el-icon :class="{ 'is-rotate': showPrompt }"><ArrowLeft /></el-icon>
    </div>
    <transition name="el-zoom-in-top">
      <div v-show="showPrompt" class="workflow-step-view__prompt-content">
        <pre>{{ haimeiPrompt }}</pre>
      </div>
    </transition>
  </div>

  <!-- qa_review -->
  <div v-if="stepStatus === 'qa_review'" class="workflow-step-view__card">
    <div class="workflow-step-view__card-icon">🔍</div>
    <h2>等待 QA 检验</h2>
    <p>步骤执行完成，等待检验通过后进入下一步</p>
    <div class="workflow-step-view__action-row">
      <el-button type="primary" size="large" :loading="executing" @click="emit('execute')">
        🔄 重新执行
      </el-button>
      <el-button plain size="large" @click="emit('go-prev')">
        ← 回到步骤{{ prevStep }}
      </el-button>
    </div>
  </div>

  <!-- completed -->
  <div v-if="stepStatus === 'completed'" class="workflow-step-view__card">
    <div class="workflow-step-view__card-icon">✅</div>
    <h2>已完成</h2>
    <div class="workflow-step-view__action-row">
      <el-button size="large" @click="emit('go-next')">
        进入步骤{{ nextStep }} →
      </el-button>
    </div>
  </div>

  <!-- rejected / error -->
  <div v-if="stepStatus === 'rejected' || stepStatus === 'error'" class="workflow-step-view__card">
    <div class="workflow-step-view__card-icon">❌</div>
    <h2>{{ statusLabelMap[stepStatus] || stepStatus }}</h2>
    <div class="workflow-step-view__action-row">
      <el-button type="primary" size="large" :loading="executing" @click="emit('execute')">
        🔄 重新执行
      </el-button>
      <el-button plain size="large" @click="emit('go-prev')">
        ← 回到步骤{{ prevStep }}
      </el-button>
    </div>
  </div>

  <!-- 执行日志 -->
  <div v-if="stageLog.length" class="workflow-step-view__log">
    <h3>📋 执行日志</h3>
    <div class="workflow-step-view__log-scroll">
      <div v-for="(msg, i) in stageLog" :key="i" class="workflow-step-view__log-msg" :class="msg.type">
        <span>
          {{ msg.type === 'stage' ? '📌' : msg.type === 'progress' ? '⏳' : msg.type === 'done' ? '✅' : msg.type === 'debug' ? '🔍' : msg.type === 'timing' ? '⏱️' : '❌' }}
        </span>
        <span style="white-space: pre-wrap">{{ msg.message }}</span>
      </div>
    </div>
  </div>

  <!-- 产物预览 -->
  <div v-if="liveContent.trim()" class="workflow-step-view__content">
    <h3>📄 产物预览</h3>
    <pre>{{ liveContent }}</pre>
  </div>
</div>
</template>

<style scoped lang="scss">
.workflow-step-view {
  max-width: 1100px; margin: 0 auto; padding: 32px 24px;

  &__header {
    display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px;
    &-left { display: flex; align-items: flex-start; gap: 16px; h1 { margin: 0; font-size: 24px; font-weight: 600; color: $text-primary; } }
  }
  &__subtitle { margin: 4px 0 0; color: $text-muted; font-size: 14px; }
  &__alert { margin-bottom: 16px; }
  &__card {
    text-align: center; padding: 40px 24px;
    background: $glass-bg;
    backdrop-filter: $frosted-blur;
    border: 1px solid $glass-border;
    border-radius: 12px;
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.05);
    h2 { color: $text-primary; }
    p { color: $text-secondary; }
  }
  &__card-icon { font-size: 48px; line-height: 1; }
  &__action-row { display: flex; gap: 12px; justify-content: center; margin-top: 24px; }
  &__executing-status { font-size: 14px; color: $primary; font-weight: 500; }
  &--executing { border-color: $border-cyan; background: rgba(0, 212, 255, 0.05); }

  &__log {
    margin-top: 24px; padding: 16px;
    background: $glass-bg;
    border: 1px solid $border-subtle;
    border-radius: 10px;
    h3 { margin: 0 0 12px; font-size: 16px; color: $text-primary; }
  }
  &__log-scroll { max-height: 400px; overflow-y: auto; }
  &__log-msg {
    padding: 6px 0; font-size: 13px; border-bottom: 1px solid $border-subtle;
    display: flex; gap: 8px; align-items: flex-start;
    color: $text-secondary;
    &.error { color: $danger; }
    &.done { color: $secondary; font-weight: 500; }
    &.timing { color: $warning; font-weight: 500; background: $warning-dim; padding: 6px 8px; border-radius: 4px; }
    &.progress { color: $primary; }
  }

  &__content {
    margin-top: 24px; padding: 16px;
    background: $glass-bg;
    border: 1px solid $border-subtle;
    border-radius: 10px;
    h3 { margin: 0 0 12px; font-size: 16px; color: $text-primary; }
    pre { font-family: $font-mono; font-size: 12px; white-space: pre-wrap; word-break: break-all; line-height: 1.6; color: $text-secondary; }
  }

  &__prompt-card { text-align: left; padding: 0; overflow: hidden; }
  &__prompt-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 16px;
    background: $primary-dim;
    border-bottom: 1px solid $border-subtle;
    cursor: pointer; font-weight: 500; font-size: 14px; color: $text-primary;
    transition: background $transition-fast;
    &:hover { background: rgba(0, 212, 255, 0.2); }
    .el-icon { transition: transform 0.3s; &.is-rotate { transform: rotate(-90deg); } }
  }
  &__prompt-content {
    max-height: 400px; overflow-y: auto; padding: 16px;
    background: $bg-surface;
    pre {
      font-family: $font-mono; font-size: 12px; white-space: pre-wrap; word-break: break-all;
      line-height: 1.6; color: $text-secondary; margin: 0;
    }
  }
}
</style>
