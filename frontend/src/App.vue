<template>
  <div id="app" :class="{ 'is-logout': !isLoggedIn }">
    <template v-if="isLoggedIn">
      <app-header />
      <div class="app-layout">
        <app-sidebar />
        <main class="app-main">
          <div class="app-main__inner">
            <router-view v-slot="{ Component }">
              <transition name="fade" mode="out-in">
                <component :is="Component" />
              </transition>
            </router-view>
          </div>
        </main>
      </div>
    </template>
    <router-view v-else />
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useAuthStore } from '@/stores/useAuthStore'
import { useWebSocketStore } from '@/stores/useWebSocketStore'
import AppHeader from '@/components/common/AppHeader.vue'
import AppSidebar from '@/components/common/AppSidebar.vue'
const authStore = useAuthStore()
const wsStore = useWebSocketStore()
const isLoggedIn = computed(() => authStore.isAuthenticated)

watch(isLoggedIn, (val) => {
  if (val && authStore.accessToken) {
    wsStore.connect(authStore.accessToken)
  } else {
    wsStore.disconnect()
  }
}, { immediate: true })
</script>

<style lang="scss">
.app-layout {
  display: flex;
  height: calc(100vh - #{$global-nav-height});
  overflow: hidden;
  position: relative;
  z-index: 1;
}

.app-main {
  flex: 1;
  overflow-y: auto;
  background: $bg-base;
  display: flex;
  flex-direction: column;

  &__inner {
    max-width: $grid-max-width;
    margin: 0 auto;
    padding: $spacing-section $spacing-xxl;
    min-height: 0;
    display: flex;
    flex-direction: column;
    flex: 1;
    position: relative;
    z-index: 1;

    &:has(.step3-view) {
      padding: 0;
    }
  }
}

.is-logout {
  background: $bg-deep;
}
</style>
