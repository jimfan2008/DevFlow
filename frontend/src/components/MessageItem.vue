<template>
  <div v-if="message.role === 'system'" class="message-system">
    <el-tag type="info" effect="plain" size="small">
      {{ message.content }}
    </el-tag>
  </div>
  <div v-else :class="['message-bubble', message.sender === 'user' ? 'is-user' : 'is-agent']">
    <el-avatar
      :class="['message-bubble__avatar', message.sender === 'user' ? 'avatar-user' : getAgentColor(message.sender)]"
      :size="40"
      shape="circle"
    >
      {{ message.sender === 'user' ? 'U' : message.sender.charAt(0).toUpperCase() }}
    </el-avatar>
    <div :class="['message-bubble__body', message.sender === 'user' ? 'body-user' : '']">
      <div :class="['message-bubble__meta', message.sender === 'user' ? 'meta-user' : '']">
        <span class="message-bubble__sender">{{ message.sender }}</span>
        <span v-if="isCurrentSpeaker" class="message-bubble__speaker">
          <span class="speaker-dot"></span>
          发言中
        </span>
        <span class="message-bubble__time">{{ formatTime(message.timestamp) }}</span>
        <el-tag v-if="agentStatus === 'typing'" size="small" type="warning" effect="plain">正在输入...</el-tag>
        <el-tag v-if="agentStatus === 'speaking'" size="small" type="success" effect="plain">发言中...</el-tag>
      </div>
      <div
        :class="['message-bubble__content', message.sender === 'user' ? 'content-user' : isCurrentSpeaker ? 'content-speaker' : 'content-agent']"
      >
        <div class="markdown-body" v-html="renderedContent"></div>
        <span v-if="message.is_streaming" class="streaming-cursor"></span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import type { Message } from '@/types'

const props = defineProps<{
  message: Message
  agentStatus?: string
  isCurrentSpeaker?: boolean
}>()

const md = new MarkdownIt({ breaks: true, html: true })

const renderedContent = computed(() => {
  return md.render(props.message.content)
})

const colorMap: Record<string, string> = {}
const colors = [
  'avatar-purple',
  'avatar-green',
  'avatar-yellow',
  'avatar-red',
  'avatar-indigo',
  'avatar-pink',
  'avatar-teal',
  'avatar-orange',
]

function getAgentColor(name: string): string {
  if (!colorMap[name]) {
    const index = Object.keys(colorMap).length % colors.length
    colorMap[name] = colors[index]
  }
  return colorMap[name]
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style lang="scss" scoped>
.message-system {
  display: flex;
  justify-content: center;
  margin: $spacing-xs 0;
}

.message-bubble {
  display: flex;
  gap: $spacing-sm;
  margin-bottom: $spacing-sm;

  &.is-user { flex-direction: row-reverse; }

  &__avatar {
    flex-shrink: 0;
    font-weight: 600;
    font-size: $caption-strong-size;

    &.avatar-user { background: $primary; }

    &.avatar-purple { background: #7c3aed; }
    &.avatar-green { background: #059669; }
    &.avatar-yellow { background: #d97706; }
    &.avatar-red { background: #dc2626; }
    &.avatar-indigo { background: #4f46e5; }
    &.avatar-pink { background: #db2777; }
    &.avatar-teal { background: #0d9488; }
    &.avatar-orange { background: #ea580c; }
  }

  &__body {
    max-width: 70%;
    &.body-user { text-align: right; }
  }

  &__meta {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    margin-bottom: $spacing-xxs;

    &.meta-user { justify-content: flex-end; }
  }

  &__sender {
    font-family: $font-text;
    font-size: $caption-strong-size;
    font-weight: $caption-strong-weight;
    letter-spacing: $caption-strong-tracking;
    color: $ink;
  }

  &__speaker {
    display: inline-flex;
    align-items: center;
    gap: $spacing-xxs;
    font-size: $fine-print-size;
    color: #22c55e;
    font-weight: 500;
  }

  &__time {
    font-size: $fine-print-size;
    color: $ink-muted-48;
  }

  &__content {
    padding: $spacing-sm $spacing-4;
    border-radius: $radius-md;
    text-align: left;
    line-height: $body-leading;

    &.content-user {
      background: $primary;
      color: $on-primary;
      border-bottom-right-radius: $radius-sm;
    }

    &.content-agent {
      background: $canvas;
      border: 1px solid $hairline;
      color: $ink;
      border-bottom-left-radius: $radius-sm;
    }

    &.content-speaker {
      background: $canvas-parchment;
      border: 1px solid $primary;
      color: $ink;
      border-bottom-left-radius: $radius-sm;
    }
  }
}

.speaker-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  background: #22c55e;
  border-radius: $radius-full;
  animation: pulse-dot 1.5s ease-in-out infinite;
}

.streaming-cursor {
  display: inline-block;
  width: 2px;
  height: 16px;
  background: currentColor;
  margin-left: 2px;
  animation: blink-cursor 0.8s step-end infinite;
  vertical-align: text-bottom;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

@keyframes blink-cursor {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.markdown-body {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: $font-text;

  :deep(p) { margin: 0; }

  :deep(ul), :deep(ol) {
    margin: $spacing-xxs 0;
    padding-left: $spacing-5;
  }

  :deep(code) {
    background: rgba(0, 0, 0, 0.06);
    padding: 1px 4px;
    border-radius: $radius-sm;
    font-size: $fine-print-size;
  }

  :deep(pre) {
    background: rgba(0, 0, 0, 0.06);
    padding: $spacing-sm;
    border-radius: $radius-sm;
    overflow-x: auto;
    margin: $spacing-xs 0;
  }
}
</style>