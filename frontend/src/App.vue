<template>
  <div id="app" :class="{ 'is-logout': !isLoggedIn }">
    <template v-if="isLoggedIn">
      <app-header />
      <div class="app-layout">
        <app-sidebar />
        <main class="app-main">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </main>
      </div>
    </template>
    <router-view v-else />
    <notification-container />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '@/stores/useAuthStore'
import AppHeader from '@/components/common/AppHeader.vue'
import AppSidebar from '@/components/common/AppSidebar.vue'
import NotificationContainer from '@/components/inbox/NotificationContainer.vue'

const authStore = useAuthStore()
const isLoggedIn = computed(() => authStore.isAuthenticated)
</script>

<style lang="scss">
.app-layout {
  display: flex;
  min-height: calc(100vh - #{$header-height});
}

.app-main {
  flex: 1;
  padding: $spacing-6;
  overflow-y: auto;
  background-color: $bg-color-body;
}

.is-logout {
  background-color: $bg-color-light;
}
</style>
