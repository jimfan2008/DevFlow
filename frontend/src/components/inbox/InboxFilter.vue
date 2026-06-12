<template>
  <div class="inbox-filter">
    <div class="inbox-filter__tabs">
      <el-radio-group v-model="status" size="small" @change="handleStatusChange">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="unread">未读</el-radio-button>
        <el-radio-button value="read">已读</el-radio-button>
      </el-radio-group>
    </div>

    <div class="inbox-filter__type">
      <el-select
        v-model="typeFilter"
        placeholder="通知类型"
        size="small"
        clearable
        @change="handleTypeChange"
      >
        <el-option label="全部类型" value="all" />
        <el-option label="任务分配" value="assigned" />
        <el-option label="新评论" value="comment" />
        <el-option label="状态变更" value="status_change" />
        <el-option label="截止提醒" value="due_reminder" />
        <el-option label="被提及" value="mention" />
      </el-select>
    </div>

    <div class="inbox-filter__search">
      <el-input
        v-model="keyword"
        placeholder="搜索通知..."
        size="small"
        :prefix-icon="Search"
        clearable
        @input="handleSearchInput"
      />
    </div>

    <div class="inbox-filter__actions">
      <el-button size="small" @click="handleReset">重置</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useInboxStore } from '@/stores/useInboxStore'
import type { NotificationType } from '@/types/api'

const inboxStore = useInboxStore()

const status = ref<'all' | 'read' | 'unread'>('all')
const typeFilter = ref<NotificationType | 'all'>('all')
const keyword = ref('')

function handleStatusChange(val: string) {
  inboxStore.setFilterStatus(val as 'all' | 'read' | 'unread')
  inboxStore.fetchNotifications(1)
}

function handleTypeChange(val: NotificationType | 'all' | '') {
  const t = val || 'all'
  inboxStore.setFilterType(t as NotificationType | 'all')
  inboxStore.fetchNotifications(1)
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
function handleSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    inboxStore.setSearchKeyword(keyword.value)
  }, 300)
}

function handleReset() {
  status.value = 'all'
  typeFilter.value = 'all'
  keyword.value = ''
  inboxStore.resetFilters()
  inboxStore.fetchNotifications(1)
}
</script>

<style lang="scss" scoped>
.inbox-filter {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  flex-wrap: wrap;
  padding: $spacing-4;
  background: $canvas;
  border-radius: $radius-lg;
  border: 1px solid $hairline;

  &__search {
    flex: 1;
    min-width: 200px;
  }

  &__actions { flex-shrink: 0; }
}
</style>
