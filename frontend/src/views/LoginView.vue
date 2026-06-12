<template>
  <div class="login-view">
    <div class="login-view__card">
      <div class="login-view__header">
        <div class="login-view__logo">D</div>
        <h2 class="login-view__title">登录 DevFlow</h2>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        @submit.prevent="handleLogin"
        class="login-view__form"
      >
        <el-form-item prop="email">
          <el-input
            v-model="form.email"
            placeholder="邮箱"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="authStore.loading"
            @click="handleLogin"
            class="login-view__submit"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <p class="login-view__footer">
        还没有账号？
        <router-link to="/register">立即注册</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/useAuthStore'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref()

const form = reactive({
  email: '',
  password: '',
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' },
  ],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    await authStore.login({ email: form.email, password: form.password })
    ElMessage.success('登录成功')
    const redirect = router.currentRoute.value.query.redirect as string
    router.push(redirect || { name: 'ProjectList' })
  } catch (e: any) {
    ElMessage.error(e.message || '登录失败，请重试')
  }
}
</script>

<style lang="scss" scoped>
.login-view {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: $canvas-parchment;

  &__card {
    width: 400px;
    padding: 48px;
    background: $canvas;
    border-radius: $radius-lg;
    border: 1px solid $hairline;
  }

  &__header {
    text-align: center;
    margin-bottom: $spacing-xl;
  }

  &__logo {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    background: $primary;
    color: $on-primary;
    font-size: 24px;
    font-weight: 600;
    border-radius: $radius-lg;
    margin-bottom: 16px;
  }

  &__title {
    margin: 0;
    font-size: $display-md-size;
    font-weight: $display-md-weight;
    font-family: $font-display;
    letter-spacing: $display-md-tracking;
    color: $ink;
  }

  &__form {
    .el-form-item:last-child {
      margin-bottom: 0;
    }
  }

  &__submit {
    width: 100%;
  }

  &__footer {
    margin-top: 24px;
    text-align: center;
    font-size: $caption-size;
    color: $ink-muted-48;

    a {
      color: $primary;
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }
  }
}
</style>
