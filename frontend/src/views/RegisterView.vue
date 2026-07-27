<template>
  <div class="register-view">
    <div class="register-view__card">
      <div class="register-view__header">
        <div class="register-view__logo">DF</div>
        <h2 class="register-view__title">注册 DevFlow</h2>
        <p class="register-view__subtitle">AI 原生多智能体开发平台</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        @submit.prevent="handleRegister"
        class="register-view__form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="email">
          <el-input
            v-model="form.email"
            placeholder="邮箱"
            :prefix-icon="Message"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="display_name">
          <el-input
            v-model="form.display_name"
            placeholder="显示名称（可选）"
            :prefix-icon="Edit"
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
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="确认密码"
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
            @click="handleRegister"
            class="register-view__submit"
          >
            注册
          </el-button>
        </el-form-item>
      </el-form>

      <p class="register-view__footer">
        已有账号？
        <router-link to="/login">立即登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Message, Edit, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/useAuthStore'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref()

const form = reactive({
  username: '',
  email: '',
  display_name: '',
  password: '',
  confirmPassword: '',
})

const validateConfirm = (_rule: any, value: string, callback: any) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度3-20个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少8个字符', trigger: 'blur' },
    {
      validator: (_rule: any, value: string, callback: any) => {
        if (!/[A-Z]/.test(value)) return callback(new Error('密码需包含大写字母'))
        if (!/[a-z]/.test(value)) return callback(new Error('密码需包含小写字母'))
        if (!/[0-9]/.test(value)) return callback(new Error('密码需包含数字'))
        callback()
      },
      trigger: 'blur'
    },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

async function handleRegister() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    await authStore.register({
      username: form.username,
      email: form.email,
      password: form.password,
      confirm_password: form.confirmPassword,
      display_name: form.display_name || undefined,
    })
    ElMessage.success('注册成功')
    router.push({ name: 'BoardList' })
  } catch (e: any) {
    if (e?.code === 'AUTH_USER_EXISTS') {
      ElMessage.error('该用户名或邮箱已注册，请直接登录或更换邮箱')
      return
    }
    ElMessage.error(e.message || '注册失败，请重试')
  }
}
</script>

<style lang="scss" scoped>
.register-view {
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
    width: 420px;
    padding: $spacing-xl;
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
    margin-bottom: $spacing-4;
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
    margin-top: $spacing-lg;
    text-align: center;
    font-family: $font-text;
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
