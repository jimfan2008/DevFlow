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
  background: $bg-color-card;
  border-left: 1px solid $border-color-light;
  display: flex;
  flex-direction: column;
  height: 100%;

  &__header {
    padding: $spacing-4;
    border-bottom: 1px solid $border-color-light;
  }

  &__title {
    margin: 0;
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: $text-color-primary;
  }

  &__body {
    flex: 1;
    overflow-y: auto;
    padding: $spacing-3;
  }

  &__empty {
    text-align: center;
    padding: $spacing-8 0;
    color: $text-color-placeholder;
  }

  &__meeting-info {
    margin-bottom: $spacing-4;
    padding: $spacing-3;
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: $radius-md;
  }

  &__meeting-tag {
    margin-bottom: $spacing-1;
  }

  &__meeting-host {
    font-size: $font-size-sm;
    color: #92400e;
    margin-top: $spacing-1;
  }

  &__meeting-speaker {
    display: flex;
    align-items: center;
    gap: $spacing-1;
    font-size: $font-size-xs;
    color: #16a34a;
    margin-top: $spacing-1;
  }

  &__items {
    display: flex;
    flex-direction: column;
    gap: $spacing-1;
  }

  &__item {
    display: flex;
    align-items: center;
    gap: $spacing-3;
    padding: $spacing-2;
    border-radius: $radius-base;
    transition: background 0.2s;

    &:hover {
      background: $bg-color-body;
    }
  }

  &__status-dot {
    width: 8px;
    height: 8px;
    border-radius: $radius-full;
    flex-shrink: 0;

    &.dot-active {
      background: #22c55e;
      animation: pulse 1.5s ease-in-out infinite;
    }

    &.dot-idle {
      background: $text-color-disabled;
    }

    &.dot-offline {
      background: #ef4444;
    }
  }

  &__item-info {
    flex: 1;
    min-width: 0;
  }

  &__item-name {
    font-weight: $font-weight-medium;
    font-size: $font-size-sm;
    color: $text-color-primary;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__item-status {
    font-size: $font-size-xs;
    color: $text-color-secondary;
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