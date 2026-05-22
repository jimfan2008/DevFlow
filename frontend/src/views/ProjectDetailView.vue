<template>
  <div class="project-detail-view" v-loading="store.loading">
    <div class="project-detail-view__header">
      <el-button :icon="ArrowLeft" text @click="router.push({ name: 'ProjectList' })">返回</el-button>
      <h2>{{ store.currentProject?.name }}</h2>
      <el-tag v-if="store.currentProject" :type="statusTagType(store.currentProject.status)">{{ statusLabel(store.currentProject.status) }}</el-tag>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="基本信息" name="info">
        <el-descriptions :column="2" border v-if="store.currentProject">
          <el-descriptions-item label="项目名称">{{ store.currentProject.name }}</el-descriptions-item>
          <el-descriptions-item label="Slug">{{ store.currentProject.slug }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusLabel(store.currentProject.status) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(store.currentProject.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ store.currentProject.description || '-' }}</el-descriptions-item>
          <el-descriptions-item label="仓库地址" :span="2">
            <el-link v-if="store.currentProject.repo_url" :href="store.currentProject.repo_url" target="_blank" type="primary">{{ store.currentProject.repo_url }}</el-link>
            <span v-else>-</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>

      <el-tab-pane label="关联需求" name="requirement">
        <el-button @click="router.push({ name: 'Requirements' })" type="primary" plain>前往需求管理</el-button>
      </el-tab-pane>

      <el-tab-pane label="任务统计" name="tasks">
        <el-table :data="tasks" stripe v-if="tasks.length">
          <el-table-column prop="title" label="任务标题" />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column prop="priority" label="优先级" width="100" />
        </el-table>
        <el-empty v-else description="暂无任务" />
      </el-tab-pane>

      <el-tab-pane label="通知列表" name="notifications">
        <el-table :data="projectNotifications" stripe v-if="projectNotifications.length">
          <el-table-column prop="title" label="标题" />
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="created_at" label="时间" width="180">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无通知" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/useProjectStore'

const router = useRouter()
const route = useRoute()
const store = useProjectStore()
const activeTab = ref('info')
const tasks = ref<any[]>([])
const projectNotifications = ref<any[]>([])

onMounted(async () => {
  const projectId = route.params.projectId as string
  await store.fetchProjectDetail(projectId)
  const [taskRes, notifRes] = await Promise.all([
    store.fetchProjectTasks(projectId),
    store.fetchProjectNotifications(projectId),
  ])
  tasks.value = taskRes || []
  projectNotifications.value = notifRes?.notifications || []
})

function statusLabel(status: string) {
  const map: Record<string, string> = { draft: '草稿', active: '进行中', completed: '已完成', archived: '已归档' }
  return map[status] || status
}

function statusTagType(status: string) {
  const map: Record<string, string> = { draft: 'info', active: '', completed: 'success', archived: 'warning' }
  return (map[status] || 'info') as any
}

function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN')
}
</script>

<style lang="scss" scoped>
.project-detail-view {
  &__header {
    display: flex;
    align-items: center;
    gap: $spacing-3;
    margin-bottom: $spacing-6;
    h2 { margin: 0; font-size: $font-size-2xl; font-weight: $font-weight-bold; }
  }
}
</style>
