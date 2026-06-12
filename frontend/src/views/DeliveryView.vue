<template>
  <div class="delivery-view">
    <div class="delivery-view__header">
      <h2 class="delivery-view__title">项目交付</h2>
    </div>

    <el-card shadow="never" class="delivery-view__card">
      <template #header>选择项目</template>
      <el-select v-model="selectedProjectId" placeholder="选择项目" style="width: 320px" @change="handleProjectChange">
        <el-option v-for="p in projectStore.projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
    </el-card>

    <template v-if="selectedProjectId">
      <el-card shadow="never" class="delivery-view__card" style="margin-top: 16px">
        <template #header>项目状态</template>
        <el-descriptions :column="2" border v-if="projectStore.currentProject">
          <el-descriptions-item label="项目名称">{{ projectStore.currentProject.name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="projectStore.currentProject.status === 'completed' ? 'success' : 'warning'">
              {{ projectStore.currentProject.status === 'completed' ? '已完成' : projectStore.currentProject.status }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never" class="delivery-view__card" style="margin-top: 16px">
        <template #header>交付操作</template>
        <el-result v-if="deliveryResult" icon="success" title="项目已成功交付" :sub-title="deliveryResult.summary || ''">
          <template #extra>
            <el-button type="primary" @click="deliveryResult = null">返回</el-button>
          </template>
        </el-result>
        <div v-else>
          <el-button type="primary" size="large" :loading="delivering" :disabled="projectStore.currentProject?.status === 'completed'" @click="handleDeliver">
            确认交付
          </el-button>
          <p style="margin-top: 12px; font-size: 13px; color: #909399;">交付前请确保所有验收报告已通过</p>
        </div>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useProjectStore } from '@/stores/useProjectStore'
import { useAcceptanceStore } from '@/stores/useAcceptanceStore'

const projectStore = useProjectStore()
const acceptanceStore = useAcceptanceStore()
const selectedProjectId = ref('')
const delivering = ref(false)
const deliveryResult = ref<any>(null)

onMounted(() => {
  projectStore.fetchProjects()
})

async function handleProjectChange(projectId: string) {
  await projectStore.fetchProjectDetail(projectId)
  deliveryResult.value = null
}

async function handleDeliver() {
  if (!selectedProjectId.value) return
  try {
    await ElMessageBox.confirm('确认交付该项目？交付后将标记项目为完成状态。', '确认交付', { type: 'warning' })
  } catch { return }

  delivering.value = true
  const result = await acceptanceStore.deliverProject(selectedProjectId.value)
  delivering.value = false

  if (result) {
    deliveryResult.value = result
    ElMessage.success('项目交付成功')
    await projectStore.fetchProjectDetail(selectedProjectId.value)
  } else {
    ElMessage.error('交付失败，请检查验收状态')
  }
}
</script>

<style lang="scss" scoped>
.delivery-view {
  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-6;
  }
  &__title {
    margin: 0;
    font-family: $font-display;
    font-size: $display-lg-size;
    font-weight: $display-lg-weight;
    line-height: $display-lg-leading;
    letter-spacing: $display-lg-tracking;
    color: $ink;
  }
  &__card {
    border-radius: $radius-lg;
  }
}
</style>
