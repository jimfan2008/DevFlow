<template>
  <div class="member-list">
    <div class="member-list__header">
      <h3 class="member-list__title">成员列表</h3>
    </div>
    <div class="member-list__body">
      <div v-if="profilesStore.profiles.length === 0" class="member-list__empty">
        <el-empty description="暂无成员" :image-size="40" />
      </div>
      <div v-else>
        <div v-if="meetingState?.isActive" class="member-list__meeting-info">
          <div class="member-list__meeting-tag">
            <el-tag type="warning" size="small" effect="plain">会议模式</el-tag>
          </div>
          <div class="member-list__meeting-host">主持: {{ meetingState.hostAgent }}</div>
          <div v-if="meetingState.currentSpeaker" class="member-list__meeting-speaker">
            <span class="speaker-indicator"></span>
            发言中: {{ meetingState.currentSpeaker }}
          </div>
        </div>
        <div class="member-list__items">
          <div
            v-for="profile in profilesStore.profiles"
            :key="profile.name"
            class="member-list__item"
          >
            <span :class="['member-list__status-dot', getStatusDotClass(profile.name)]"></span>
            <div class="member-list__item-info">
              <div class="member-list__item-name">{{ profile.name }}</div>
              <div class="member-list__item-status">{{ getStatusText(profile.name) }}</div>
            </div>
            <el-tag
              v-if="meetingState?.isActive && profile.name === meetingState.hostAgent"
              size="small"
              type="warning"
              effect="plain"
            >主持</el-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useProfilesStore } from '@/stores/profiles'

const chatStore = useChatStore()
const profilesStore = useProfilesStore()

const meetingState = computed(() => {
  const states = chatStore.meetingStates
  const keys = Object.keys(states)
  if (keys.length > 0) {
    return states[keys[0]]
  }
  return null
})

function getAgentStatus(profileName: string): string {
  const states = chatStore.agentStatuses
  const groupIds = Object.keys(states)
  for (const gid of groupIds) {
    const status = states[gid][profileName]
    if (status) return status
  }
  return 'idle'
}

function getStatusDotClass(profileName: string): string {
  const profile = profilesStore.profiles.find(p => p.name === profileName)
  if (!profile?.is_running) return 'dot-offline'

  const status = getAgentStatus(profileName)
  switch (status) {
    case 'typing':
    case 'speaking':
      return 'dot-active'
    case 'idle':
      return 'dot-idle'
    default:
      return 'dot-idle'
  }
}

function getStatusText(profileName: string): string {
  const profile = profilesStore.profiles.find(p => p.name === profileName)
  if (!profile?.is_running) return '离线'

  const status = getAgentStatus(profileName)
  switch (status) {
    case 'typing':
      return '正在输入...'
    case 'speaking':
      return '发言中...'
    case 'idle':
      return '在线'
    default:
      return '在线'
  }
}
</script>

<style lang="scss" scoped>
.member-list {
  background: $canvas;
  display: flex;
  flex-direction: column;
  height: 100%;

  &__header {
    padding: $spacing-4;
    border-bottom: 1px solid $hairline;
  }

  &__title {
    margin: 0;
    font-family: $font-text;
    font-size: $body-strong-size;
    font-weight: $body-strong-weight;
    letter-spacing: $body-strong-tracking;
    color: $ink;
  }

  &__body {
    flex: 1;
    overflow-y: auto;
    padding: $spacing-sm;
  }

  &__empty {
    text-align: center;
    padding: $spacing-lg 0;
    color: $ink-muted-48;
  }

  &__meeting-info {
    margin-bottom: $spacing-4;
    padding: $spacing-sm;
    background: mix(white, #f59e0b, 90%);
    border: 1px solid #f59e0b;
    border-radius: $radius-sm;
  }

  &__meeting-tag { margin-bottom: $spacing-xxs; }

  &__meeting-host {
    font-family: $font-text;
    font-size: $body-size;
    color: mix(black, #f59e0b, 40%);
    margin-top: $spacing-xxs;
  }

  &__meeting-speaker {
    display: flex;
    align-items: center;
    gap: $spacing-xxs;
    font-size: $fine-print-size;
    color: #10b981;
    margin-top: $spacing-xxs;
  }

  &__items {
    display: flex;
    flex-direction: column;
    gap: $spacing-xxs;
  }

  &__item {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-xs;
    border-radius: $radius-sm;
    transition: background 0.15s;

    &:hover { background: $canvas-parchment; }
  }

  &__status-dot {
    width: 8px;
    height: 8px;
    border-radius: $radius-full;
    flex-shrink: 0;

    &.dot-active { background: #10b981; animation: pulse 1.5s ease-in-out infinite; }
    &.dot-idle { background: $ink-muted-48; }
    &.dot-offline { background: #ef4444; }
  }

  &__item-info {
    flex: 1;
    min-width: 0;
  }

  &__item-name {
    font-family: $font-text;
    font-size: $body-strong-size;
    font-weight: $body-strong-weight;
    letter-spacing: $body-strong-tracking;
    color: $ink;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__item-status {
    font-size: $caption-size;
    color: $ink-muted-48;
  }
}

.speaker-indicator {
  display: inline-block;
  width: 6px;
  height: 6px;
  background: #22c55e;
  border-radius: $radius-full;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}
</style>