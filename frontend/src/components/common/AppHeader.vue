<template>
  <header class="global-nav">
    <div class="global-nav__left">
      <router-link to="/boards" class="global-nav__logo">
        <span class="global-nav__mark"></span>
        <span class="global-nav__title">DevFlow</span>
      </router-link>
    </div>

    <nav class="global-nav__center">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="global-nav__link"
        :class="{ active: isActive(item.path) }"
      >
        {{ item.label }}
      </router-link>
    </nav>

    <div class="global-nav__right">
      <el-input
        v-model="searchQuery"
        placeholder="搜索"
        :prefix-icon="Search"
        clearable
        class="global-nav__search"
        @keyup.enter="handleSearch"
      />
      <button class="global-nav__icon-btn" @click="goToInbox">
        <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
          <Bell />
        </el-badge>
      </button>
      <el-dropdown trigger="click" @command="handleCommand">
        <button class="global-nav__user-btn">
          <el-avatar :size="22" class="global-nav__avatar">{{ displayName.charAt(0).toUpperCase() }}</el-avatar>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">个人资料</el-dropdown-item>
            <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Search, Bell } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/useAuthStore'
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const searchQuery = ref('')
const displayName = authStore.displayName || authStore.username || 'User'
const unreadCount = 0

const navItems = [
  { path: '/projects', label: '项目' },
  { path: '/agents', label: 'Agent' },
  { path: '/task-board', label: '任务' },
  { path: '/chat', label: '对话' },
  { path: '/boards', label: '看板' },
]

function isActive(path: string) {
  return route.path.startsWith(path)
}

function handleSearch() {
  if (searchQuery.value.trim()) {
    router.push({ name: 'BoardList', query: { search: searchQuery.value.trim() } })
  }
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
.global-nav {
  display: flex;
  align-items: center;
  height: $global-nav-height;
  padding: 0 $spacing-xxl;
  background: $surface-black;
  color: $body-on-dark;
  position: sticky;
  top: 0;
  z-index: 200;

  &__left {
    display: flex;
    align-items: center;
    margin-right: $spacing-xl;
  }

  &__logo {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    text-decoration: none;
    color: $body-on-dark;
  }

  &__mark {
    font-size: 18px;
    line-height: 1;
  }

  &__title {
    font-family: $font-text;
    font-size: $nav-link-size;
    font-weight: $nav-link-weight;
    letter-spacing: $nav-link-tracking;
    opacity: 0.8;
  }

  &__center {
    flex: 1;
    display: flex;
    align-items: center;
    gap: $spacing-5;
  }

  &__link {
    font-family: $font-text;
    font-size: $nav-link-size;
    font-weight: $nav-link-weight;
    letter-spacing: $nav-link-tracking;
    color: rgba(255, 255, 255, 0.65);
    text-decoration: none;
    transition: color 0.15s;
    white-space: nowrap;

    &:hover { color: $body-on-dark; }
    &.active { color: $body-on-dark; }
  }

  &__right {
    display: flex;
    align-items: center;
    gap: $spacing-3;
  }

  &__search {
    width: 180px;

    :deep(.el-input__wrapper) {
      background: rgba(255, 255, 255, 0.12);
      border: none;
      border-radius: $radius-pill;
      box-shadow: none;
      height: 28px;
      padding: 0 12px;
    }

    :deep(.el-input__inner) {
      color: $body-on-dark;
      font-family: $font-text;
      font-size: $nav-link-size;
      &::placeholder { color: rgba(255, 255, 255, 0.4); }
    }

    :deep(.el-input__prefix) {
      color: rgba(255, 255, 255, 0.4);
    }
  }

  &__icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    color: rgba(255, 255, 255, 0.65);
    background: transparent;
    border: none;
    border-radius: $radius-pill;
    cursor: pointer;
    transition: color 0.15s;
    &:hover { color: $body-on-dark; }
  }

  &__user-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: transparent;
    border: none;
    border-radius: $radius-pill;
    cursor: pointer;
  }

  &__avatar {
    background: rgba(255, 255, 255, 0.2) !important;
    color: $body-on-dark !important;
    font-size: 11px !important;
    font-weight: 600;
  }
}
</style>
