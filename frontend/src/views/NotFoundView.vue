<template>
  <div class="not-found">
    <div class="not-found__content">
      <h1 class="not-found__code">404</h1>
      <h2 class="not-found__title">页面不存在</h2>
      <p class="not-found__description">您访问的页面不存在或已被移除</p>
      <el-button type="primary" @click="goHome">返回首页</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  router.push({ name: 'BoardList' })
}
</script>

<style lang="scss" scoped>
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;

  &__content {
    text-align: center;
  }

  &__code {
    font-size: 96px;
    font-weight: $font-weight-bold;
    color: $primary-color;
    margin: 0;
    line-height: 1;
  }

  &__title {
    font-size: $font-size-3xl;
    color: $text-color-primary;
    margin: 16px 0 8px;
  }

  &__description {
    font-size: $font-size-base;
    color: $text-color-secondary;
    margin: 0 0 24px;
  }
}
</style>
