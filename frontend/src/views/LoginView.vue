<template>
  <div class="login-view">
    <div class="login-view__card">
      <div class="login-view__header">
        <div class="login-view__logo">DF</div>
        <h2 class="login-view__title">登录 DevFlow</h2>
        <p class="login-view__subtitle">AI 原生多智能体开发平台</p>
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
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: $bg-deep;
  overflow: hidden;

  // Animated gradient orbs
  &::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background:
      radial-gradient(ellipse at 30% 20%, rgba(0, 212, 255, 0.08) 0%, transparent 50%),
      radial-gradient(ellipse at 70% 80%, rgba(139, 92, 246, 0.06) 0%, transparent 50%),
      radial-gradient(ellipse at 50% 50%, rgba(52, 211, 153, 0.04) 0%, transparent 50%);
    animation: bg-shift 12s ease-in-out infinite alternate;
    pointer-events: none;
  }

  // Grid overlay
  &::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image:
      linear-gradient(rgba(0, 212, 255, 0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0, 212, 255, 0.04) 1px, transparent 1px);
    background-size: 40px 40px;
    mask-image: radial-gradient(ellipse at center, black 30%, transparent 70%);
    -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 70%);
    pointer-events: none;
  }

  @keyframes bg-shift {
    0%   { transform: translate(0%, 0%) rotate(0deg); }
    100% { transform: translate(5%, 5%) rotate(3deg); }
  }

  &__card {
    position: relative;
    z-index: 1;
    width: 400px;
    padding: 48px;
    background: $glass-bg;
    backdrop-filter: $frosted-blur;
    -webkit-backdrop-filter: $frosted-blur;
    border-radius: 16px;
    border: 1px solid $glass-border;
    box-shadow: 0 0 40px rgba(0, 212, 255, 0.08), 0 20px 60px rgba(0, 0, 0, 0.4);
    animation: card-enter 0.5s ease-out;
  }

  @keyframes card-enter {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  &__header {
    text-align: center;
    margin-bottom: $spacing-xl;
  }

  &__logo {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 52px;
    height: 52px;
    background: $gradient-primary;
    color: $text-inverse;
    font-family: $font-mono;
    font-size: 22px;
    font-weight: 700;
    border-radius: 14px;
    margin-bottom: 16px;
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
  }

  &__title {
    margin: 0;
    font-family: $font-display;
    font-size: $display-md-size;
    font-weight: 600;
    color: $text-primary;
  }

  &__subtitle {
    margin: 8px 0 0;
    font-size: $caption-size;
    color: $text-muted;
    font-family: $font-text;
  }

  &__form {
    .el-form-item:last-child {
      margin-bottom: 0;
    }
  }

  &__submit {
    width: 100%;
    height: 44px;
  }

  &__footer {
    margin-top: 24px;
    text-align: center;
    font-size: $caption-size;
    color: $text-muted;

    a {
      color: $primary;
      text-decoration: none;
      font-weight: 500;
      &:hover { text-decoration: underline; }
    }
  }
}
</style>
