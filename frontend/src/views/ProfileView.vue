<template>
  <div class="profile-view" v-loading="authStore.loading">
    <div class="profile-view__card">
      <h2 class="profile-view__title">个人资料</h2>

      <el-form
        ref="profileFormRef"
        :model="profileForm"
        :rules="profileRules"
        label-width="100px"
        v-if="user"
      >
        <el-form-item label="头像">
          <el-avatar :size="64">{{ user.display_name?.charAt(0) || '?' }}</el-avatar>
        </el-form-item>
        <el-form-item label="用户名">
          <span>{{ user.username }}</span>
        </el-form-item>
        <el-form-item label="邮箱">
          <span>{{ user.email }}</span>
        </el-form-item>
        <el-form-item label="角色">
          <el-tag size="small">{{ user.role }}</el-tag>
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="profileForm.display_name" placeholder="输入显示名称" maxlength="30" />
        </el-form-item>
        <el-form-item label="头像URL" prop="avatar_url">
          <el-input v-model="profileForm.avatar_url" placeholder="头像URL（可选）" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="savingProfile" @click="handleSaveProfile">
            保存修改
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="profile-view__card">
      <h2 class="profile-view__title">修改密码</h2>

      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="100px"
      >
        <el-form-item label="当前密码" prop="current_password">
          <el-input
            v-model="passwordForm.current_password"
            type="password"
            placeholder="输入当前密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            placeholder="输入新密码"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="savingPassword" @click="handleChangePassword">
            修改密码
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="profile-view__card">
      <h2 class="profile-view__title">负载概览</h2>
      <WorkloadChart
        :members="workloadMembers"
        :summary="workloadSummary"
        :loading="workloadLoading"
        title="我的任务负载"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/useAuthStore'
import { workloadApi } from '@/api'
import WorkloadChart from '@/components/workload/WorkloadChart.vue'
import type { WorkloadMember, WorkloadSummary } from '@/types/api'

const authStore = useAuthStore()
const user = computed(() => authStore.currentUser)

const profileFormRef = ref()
const passwordFormRef = ref()
const savingProfile = ref(false)
const savingPassword = ref(false)

const workloadMembers = ref<WorkloadMember[]>([])
const workloadSummary = ref<WorkloadSummary | null>(null)
const workloadLoading = ref(false)

const profileForm = reactive({
  display_name: '',
  avatar_url: '',
})

const profileRules = {
  display_name: [{ max: 30, message: '不超过30个字符', trigger: 'blur' }],
}

const passwordForm = reactive({
  current_password: '',
  new_password: '',
})

const passwordRules = {
  current_password: [
    { required: true, message: '请输入当前密码', trigger: 'blur' },
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' },
  ],
}

onMounted(() => {
  if (user.value) {
    profileForm.display_name = user.value.display_name || ''
    profileForm.avatar_url = user.value.avatar_url || ''
  }
  fetchWorkload()
})

async function handleSaveProfile() {
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return

  savingProfile.value = true
  try {
    await authStore.updateProfile({
      display_name: profileForm.display_name || undefined,
      avatar_url: profileForm.avatar_url || undefined,
    })
    ElMessage.success('资料已更新')
  } catch (e: any) {
    ElMessage.error(e.message || '更新失败')
  } finally {
    savingProfile.value = false
  }
}

async function handleChangePassword() {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return

  savingPassword.value = true
  try {
    await authStore.changePassword({
      current_password: passwordForm.current_password,
      new_password: passwordForm.new_password,
    })
    ElMessage.success('密码已修改')
    passwordForm.current_password = ''
    passwordForm.new_password = ''
  } catch (e: any) {
    ElMessage.error(e.message || '密码修改失败')
  } finally {
    savingPassword.value = false
  }
}

async function fetchWorkload() {
  if (!user.value) return
  workloadLoading.value = true
  try {
    const res = await workloadApi.getUser(user.value.id)
    if (res.data) {
      workloadMembers.value = [res.data]
      workloadSummary.value = {
        total_tasks: res.data.total_tasks,
        total_members: 1,
        avg_tasks_per_member: res.data.total_tasks,
        overloaded_members: res.data.overload ? 1 : 0,
        underloaded_members: res.data.underload ? 1 : 0,
      }
    }
  } catch {
    // silent
  } finally {
    workloadLoading.value = false
  }
}
</script>

<style lang="scss" scoped>
.profile-view {
  max-width: 800px;
  display: flex;
  flex-direction: column;
  gap: $spacing-6;

  &__card {
    background: $canvas;
    border-radius: $radius-lg;
    padding: $spacing-6;
    border: 1px solid rgba(0, 0, 0, 0.06);
  }

  &__title {
    margin: 0 0 $spacing-6;
    font-family: $font-display;
    font-size: $display-md-size;
    font-weight: $display-md-weight;
    line-height: $display-md-leading;
    letter-spacing: $display-md-tracking;
    color: $ink;
    padding-bottom: $spacing-4;
    border-bottom: 1px solid $hairline;
  }
}
</style>
