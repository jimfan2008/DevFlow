<template>
  <div class="inbox-list" v-loading="loading">
    <div v-if="notifications.length === 0" class="inbox-list__empty">
      <EmptyState type="inbox" title="暂无通知" description="当有新的通知时，会在这里显示" />
    </div>

    <div v-else class="inbox-list__items">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        class="inbox-list__item"
        :class="{ 'is-unread': !notification.is_read }"
        @click="handleClick(notification)"
      >
        <div class="inbox-list__item-indicator">
          <span v-if="!notification.is_read" class="inbox-list__dot" />
        </div>

        <div class="inbox-list__item-content">
          <div class="inbox-list__item-header">
            <span class="inbox-list__item-type">{{ typeLabel(notification.type) }}</span>
            <span class="inbox-list__item-time">{{ formatTime(notification.created_at) }}</span>
          </div>
          <h4 class="inbox-list__item-title">{{ notification.title }}</h4>
          <p class="inbox-list__item-body">{{ notification.body }}</p>
          <div class="inbox-list__item-actor" v-if="notification.actor">
            <el-avatar :size="18">{{ notification.actor.display_name?.charAt(0) }}</el-avatar>
            <span>{{ notification.actor.display_name }}</span>
          </div>
        </div>

        <div class="inbox-list__item-actions">
          <el-button
            v-if="!notification.is_read"
            text
            size="small"
            @click.stop="handleMarkRead(notification.id)"
          >
            标为已读
          </el-button>
          <el-button
            text
            size="small"
            type="danger"
            @click.stop="handleDelete(notification.id)"
          >
            删除
          </el-button>
        </div>
      </div>
    </div>

    <div v-if="totalPages > 1" class="inbox-list__pagination">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="totalItems"
        layout="prev, pager, next"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useInboxStore } from '@/stores/useInboxStore'
import EmptyState from '@/components/common/EmptyState.vue'
import type { InboxNotification } from '@/types/api'

const router = useRouter()
const inboxStore = useInboxStore()

const notifications = computed(() => inboxStore.filteredNotifications)
const loading = computed(() => inboxStore.loading)
const currentPage = computed(() => inboxStore.currentPage)
const pageSize = computed(() => inboxStore.pageSize)
const totalItems = computed(() => inboxStore.totalItems)
const totalPages = computed(() => Math.ceil(totalItems.value / pageSize.value))

const typeLabelMap = computed(() => inboxStore.notificationTypeLabel)

function typeLabel(type: string): string {
  return (typeLabelMap.value as any)[type] || type
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

function handleClick(notification: InboxNotification) {
  if (!notification.is_read) {
    inboxStore.markAsRead(notification.id)
  }
  if (notification.task_id && notification.board_id) {
    router.push({
      name: 'TaskDetail',
      params: { boardId: notification.board_id, taskId: notification.task_id },
    })
  }
}

async function handleMarkRead(id: string) {
  try {
    await inboxStore.markAsRead(id)
  } catch {
    ElMessage.error('标记已读失败')
  }
}

async function handleDelete(id: string) {
  try {
    await inboxStore.deleteNotification(id)
    ElMessage.success('通知已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}

function handlePageChange(page: number) {
  inboxStore.fetchNotifications(page)
}
</script>

<style lang="scss" scoped>
.inbox-list {
  &__empty { padding: 60px 0; }

  &__items {
    display: flex;
    flex-direction: column;
    gap: 1px;
    background: $hairline;
    border-radius: $radius-lg;
    overflow: hidden;
  }

  &__item {
    display: flex;
    align-items: flex-start;
    padding: $spacing-4;
    background: $canvas;
    cursor: pointer;
    transition: background 0.15s;
    gap: $spacing-sm;

    &:hover { background: $canvas-parchment; }

    &.is-unread {
      background: mix(white, $primary, 95%);
      &:hover { background: mix(white, $primary, 92%); }
    }
  }

  &__dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: $primary;
    border-radius: $radius-full;
    margin-top: 6px;
  }

  &__item-indicator { width: 16px; flex-shrink: 0; }

  &__item-content {
    flex: 1;
    min-width: 0;
  }

  &__item-header {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    margin-bottom: $spacing-xxs;
  }

  &__item-type {
    font-family: $font-text;
    font-size: $fine-print-size;
    color: $primary;
    background: mix(white, $primary, 95%);
    padding: 1px 6px;
    border-radius: $radius-sm;
  }

  &__item-time {
    font-size: $fine-print-size;
    color: $ink-muted-48;
    margin-left: auto;
  }

  &__item-title {
    margin: 0 0 2px;
    font-family: $font-text;
    font-size: $body-strong-size;
    font-weight: $body-strong-weight;
    letter-spacing: $body-strong-tracking;
    color: $ink;
  }

  &__item-body {
    margin: 0;
    font-size: $body-size;
    color: $ink-muted-48;
    line-height: $body-leading;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__item-actor {
    display: flex;
    align-items: center;
    gap: $spacing-xxs;
    margin-top: $spacing-xxs;
    font-size: $fine-print-size;
    color: $ink-muted-48;
  }

  &__item-actions {
    display: flex;
    gap: $spacing-xxs;
    flex-shrink: 0;
    opacity: 0;
    transition: opacity 0.15s;
  }

  &__item:hover &__item-actions { opacity: 1; }

  &__pagination {
    display: flex;
    justify-content: center;
    padding: $spacing-4;
  }
}
</style>
