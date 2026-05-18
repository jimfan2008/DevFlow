<template>
  <header class="app-header">
    <div class="app-header__left">
      <router-link to="/boards" class="app-header__logo">
        <span class="app-header__logo-icon">D</span>
        <span class="app-header__logo-text">DevFlow</span>
      </router-link>
    </div>

    <div class="app-header__center">
      <el-input
        v-model="searchQuery"
        placeholder="搜索任务..."
        :prefix-icon="Search"
        clearable
        size="small"
        class="app-header__search"
        @keyup.enter="handleSearch"
      />
    </div>

    <div class="app-header__right">
      <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
        <el-button
          :icon="Bell"
          circle
          size="small"
          @click="goToInbox"
        />
      </el-badge>

      <el-dropdown trigger="click" @command="handleCommand">
        <span class="app-header__user">
          <el-avatar :size="28">{{ displayName.charAt(0).toUpperCase() }}</el-avatar>
          <span class="app-header__username">{{ displayName }}</span>
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>个人资料
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              <el-icon><SwitchButton /></el-icon>退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Bell, ArrowDown, User, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/useAuthStore'
import { useInboxStore } from '@/stores/useInboxStore'

const router = useRouter()
const authStore = useAuthStore()
const inboxStore = useInboxStore()

const searchQuery = ref('')
const displayName = authStore.displayName
const unreadCount = inboxStore.unreadCount

function handleSearch() {
  if (searchQuery.value.trim()) {
    router.push({ name: 'BoardList', query: { search: searchQuery.value.trim() } })
  }
}

function goToInbox() {
  router.push({ name: 'Inbox' })
}

function handleCommand(command: string) {
  if (command === 'profile') {
    router.push({ name: 'Profile' })
  } else if (command === 'logout') {
    authStore.logout()
    router.push({ name: 'Login' })
  }
}
</script>

<style lang="scss" scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: $header-height;
  padding: 0 $spacing-6;
  background: $bg-color-card;
  border-bottom: 1px solid $border-color-light;
  box-shadow: $shadow-sm;
  position: sticky;
  top: 0;
  z-index: 100;

  &__left {
    display: flex;
    align-items: center;
  }

  &__logo {
    display: flex;
    align-items: center;
    gap: 8px;
    text-decoration: none;
  }

  &__logo-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: $primary-color;
    color: $text-color-inverse;
    font-weight: $font-weight-bold;
    font-size: $font-size-lg;
    border-radius: $radius-md;
  }

  &__logo-text {
    font-size: $font-size-xl;
    font-weight: $font-weight-semibold;
    color: $text-color-primary;
  }

  &__center {
    flex: 1;
    display: flex;
    justify-content: center;
    max-width: 400px;
    margin: 0 $spacing-6;
  }

  &__search {
    width: 100%;
  }

  &__right {
    display: flex;
    align-items: center;
    gap: $spacing-4;
  }

  &__user {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: $radius-base;
    transition: background 0.2s;

    &:hover {
      background: $bg-color-body;
    }
  }

  &__username {
    font-size: $font-size-sm;
    color: $text-color-primary;
  }
}
</style>
