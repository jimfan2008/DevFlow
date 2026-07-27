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
    box-shadow: 0 0 8px rgba(255, 255, 255, 0.1);

    &.avatar-user {
      background: $gradient-primary !important;
      box-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
    }

    &.avatar-purple { background: #7c3aed !important; box-shadow: 0 0 8px rgba(124, 58, 237, 0.3); }
    &.avatar-green { background: #059669 !important; box-shadow: 0 0 8px rgba(5, 150, 105, 0.3); }
    &.avatar-yellow { background: #d97706 !important; box-shadow: 0 0 8px rgba(217, 119, 6, 0.3); }
    &.avatar-red { background: #dc2626 !important; box-shadow: 0 0 8px rgba(220, 38, 38, 0.3); }
    &.avatar-indigo { background: #4f46e5 !important; box-shadow: 0 0 8px rgba(79, 70, 229, 0.3); }
    &.avatar-pink { background: #db2777 !important; box-shadow: 0 0 8px rgba(219, 39, 119, 0.3); }
    &.avatar-teal { background: #0d9488 !important; box-shadow: 0 0 8px rgba(13, 148, 136, 0.3); }
    &.avatar-orange { background: #ea580c !important; box-shadow: 0 0 8px rgba(234, 88, 12, 0.3); }
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
    color: $text-primary;
  }

  &__speaker {
    display: inline-flex;
    align-items: center;
    gap: $spacing-xxs;
    font-size: $fine-print-size;
    color: $secondary;
    font-weight: 500;
  }

  &__time {
    font-size: $fine-print-size;
    color: $text-muted;
  }

  &__content {
    padding: $spacing-sm $spacing-4;
    border-radius: 12px;
    text-align: left;
    line-height: $body-leading;

    &.content-user {
      background: $gradient-primary;
      color: $text-inverse;
      border-bottom-right-radius: 6px;
      box-shadow: 0 2px 8px rgba(0, 212, 255, 0.2);
    }

    &.content-agent {
      background: $glass-bg;
      backdrop-filter: $frosted-blur;
      border: 1px solid $glass-border;
      color: $text-primary;
      border-bottom-left-radius: 6px;
    }

    &.content-speaker {
      background: $primary-dim;
      border: 1px solid $border-cyan;
      color: $text-primary;
      border-bottom-left-radius: 6px;
      box-shadow: 0 0 10px rgba(0, 212, 255, 0.08);
    }
  }
}

.speaker-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  background: $secondary;
  border-radius: $radius-full;
  box-shadow: 0 0 6px rgba(52, 211, 153, 0.5);
  animation: pulse-dot 1.5s ease-in-out infinite;
}

.streaming-cursor {
  display: inline-block;
  width: 2px;
  height: 16px;
  background: $primary;
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
    background: rgba(255, 255, 255, 0.1);
    color: $primary;
    padding: 1px 4px;
    border-radius: 4px;
    font-family: $font-mono;
    font-size: $fine-print-size;
  }

  :deep(pre) {
    background: rgba(0, 0, 0, 0.3);
    padding: $spacing-sm;
    border-radius: 8px;
    overflow-x: auto;
    margin: $spacing-xs 0;
    border: 1px solid $border-subtle;

    code {
      background: transparent;
      color: $text-secondary;
    }
  }

  :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: $spacing-xs 0;
    th, td {
      border: 1px solid $border-subtle;
      padding: 6px 10px;
      text-align: left;
    }
    th { background: rgba(255, 255, 255, 0.05); color: $text-primary; }
    td { color: $text-secondary; }
  }

  :deep(blockquote) {
    border-left: 3px solid $primary;
    margin: $spacing-xs 0;
    padding: 4px 12px;
    color: $text-muted;
    background: rgba(0, 212, 255, 0.04);
    border-radius: 0 4px 4px 0;
  }

  :deep(hr) {
    border: none;
    border-top: 1px solid $border-subtle;
    margin: $spacing-sm 0;
  }

  :deep(strong) { color: $text-primary; }

  :deep(a) { color: $primary; }
}
</style>