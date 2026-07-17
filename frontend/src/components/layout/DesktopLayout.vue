<template>
  <div v-if="isDesktop" class="desktop-layout">
    <div class="desktop-layout__column" :class="['desktop-layout__sidebar', { collapsed: sidebarCollapsed }]">
      <button class="desktop-layout__toggle" @click="toggleSidebar"></button>
      <div
        v-for="item in menuItems"
        :key="item"
        class="desktop-layout__menu-item"
        :class="{ active: activeMenuItem === item }"
        @click="activeMenuItem = item"
      >
        {{ item }}
      </div>
    </div>
    <div class="desktop-layout__column desktop-layout__content" style="flex: 1">
      <h1 class="desktop-layout__page-title">页面标题</h1>
    </div>
    <div class="desktop-layout__column desktop-layout__detail" v-show="detailVisible">
      <button class="desktop-layout__close-btn" @click="detailVisible = false"></button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const BREAKPOINT = 1280

const isDesktop = ref(window.innerWidth >= BREAKPOINT)
const sidebarCollapsed = ref(false)
const detailVisible = ref(true)
const activeMenuItem = ref('')
const menuItems = ['菜单1', '菜单2', '菜单3']

function handleResize() {
  isDesktop.value = window.innerWidth >= BREAKPOINT
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>
