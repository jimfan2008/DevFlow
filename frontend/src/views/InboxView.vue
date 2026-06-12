<template>
  <div class="inbox-view">
    <div class="inbox-view__header">
      <div class="inbox-view__title-section">
        <h2 class="inbox-view__title">收件箱</h2>
        <el-badge :value="inboxStore.unreadCount" :hidden="inboxStore.unreadCount === 0">
          <span class="inbox-view__subtitle">通知和提醒</span>
        </el-badge>
      </div>
      <div class="inbox-view__actions">
        <el-button
          size="small"
          :disabled="inboxStore.unreadCount === 0"
          :loading="markAllLoading"
          @click="handleMarkAllRead"
        >
          全部标记已读
        </el-button>
        <el-button size="small" @click="handleRefresh" :loading="inboxStore.loading">
          刷新
        </el-button>
      </div>
    </div>

    <InboxFilter />

    <div class="inbox-view__list">
      <InboxList />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useInboxStore } from '@/stores/useInboxStore'
import InboxFilter from '@/components/inbox/InboxFilter.vue'
import InboxList from '@/components/inbox/InboxList.vue'

const inboxStore = useInboxStore()
const markAllLoading = ref(false)

onMounted(() => {
  inboxStore.fetchNotifications(1)
})

async function handleMarkAllRead() {
  markAllLoading.value = true
  try {
    await inboxStore.markAllAsRead()
    ElMessage.success('已全部标记为已读')
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    markAllLoading.value = false
  }
}

function handleRefresh() {
  inboxStore.fetchNotifications(1)
}
</script>

<style lang="scss" scoped>
.inbox-view {
  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-4;
  }

  &__title-section {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  &__title {
    margin: 0;
    font-family: $font-display;
    font-size: $display-lg-size;
    font-weight: $display-lg-weight;
    line-height: $display-lg-leading;
    letter-spacing: $display-lg-tracking;
    color: $ink;
  }

  &__subtitle {
    font-size: $caption-size;
    color: $ink-muted-48;
  }

  &__actions {
    display: flex;
    gap: $spacing-xs;
  }

  &__list {
    margin-top: $spacing-4;
  }
}
</style>
