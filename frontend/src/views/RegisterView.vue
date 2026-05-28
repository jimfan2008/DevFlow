<template>
  <div class="register-view">
    <div class="register-view__card">
      <div class="register-view__header">
        <div class="register-view__logo">D</div>
        <h2 class="register-view__title">注册 DevFlow</h2>
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
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: $bg-color-body;

  &__card {
    width: 420px;
    padding: 40px;
    background: $bg-color-card;
    border-radius: $radius-lg;
    box-shadow: $shadow-lg;
  }

  &__header {
    text-align: center;
    margin-bottom: 32px;
  }

  &__logo {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    background: $primary-color;
    color: $text-color-inverse;
    font-size: 24px;
    font-weight: $font-weight-bold;
    border-radius: $radius-lg;
    margin-bottom: 16px;
  }

  &__title {
    margin: 0;
    font-size: $font-size-2xl;
    color: $text-color-primary;
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
    font-size: $font-size-sm;
    color: $text-color-secondary;

    a {
      color: $primary-color;
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }
  }
}
</style>
