<template>
  <div class="agent-detail-view" v-loading="store.loading">
    <div class="agent-detail-view__header">
      <el-button :icon="ArrowLeft" text @click="router.push({ name: 'AgentList' })">返回</el-button>
      <h2>{{ store.currentAgent?.name }}</h2>
      <el-tag v-if="store.currentAgent" :type="store.currentAgent.status === 'online' ? 'success' : 'info'" effect="dark">
        {{ store.currentAgent.status === 'online' ? '在线' : store.currentAgent.status === 'busy' ? '忙碌' : '离线' }}
      </el-tag>
    </div>

    <template v-if="store.currentAgent">
      <el-row :gutter="16">
        <el-col :span="14">
          <el-card shadow="never">
            <template #header>配置信息</template>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="Agent类型">{{ store.currentAgent.agent_type === 'hermes' ? 'Hermes Agent' : '编程Agent' }}</el-descriptions-item>
              <el-descriptions-item label="API端点">{{ store.currentAgent.api_endpoint || '-' }}</el-descriptions-item>
              <el-descriptions-item label="版本">{{ store.currentAgent.version || '-' }}</el-descriptions-item>
              <el-descriptions-item label="发现者">{{ store.currentAgent.discovered_by || '-' }}</el-descriptions-item>
              <el-descriptions-item label="关联Hermes">{{ store.currentAgent.hermes_agent_id || '-' }}</el-descriptions-item>
              <el-descriptions-item label="最后心跳">{{ store.currentAgent.last_heartbeat_at ? formatTime(store.currentAgent.last_heartbeat_at) : '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>

        <el-col :span="10">
          <el-card shadow="never">
            <template #header>技能列表</template>
            <div v-if="store.currentAgent.capabilities?.length">
              <el-tag v-for="cap in store.currentAgent.capabilities" :key="cap" style="margin: 4px">{{ cap }}</el-tag>
            </div>
            <el-empty v-else description="暂无技能" :image-size="60" />
          </el-card>

          <el-card shadow="never" style="margin-top: 16px">
            <template #header>Gateway状态</template>
            <div class="agent-detail-view__gateway">
              <span :class="['agent-detail-view__status-dot', store.currentAgent.status === 'online' ? 'online' : 'offline']" />
              <span>{{ store.currentAgent.status === 'online' ? 'Gateway已连接' : 'Gateway未连接' }}</span>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <div style="margin-top: 16px; display: flex; gap: 8px;">
        <el-button v-if="store.currentAgent.agent_type === 'hermes'" type="primary" @click="handleSkillDiscovery">触发Skill发现</el-button>
        <el-button type="danger" plain @click="handleDelete">移除Agent</el-button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAgentStore } from '@/stores/useAgentStore'

const router = useRouter()
const route = useRoute()
const store = useAgentStore()

onMounted(() => {
  const agentId = route.params.agentId as string
  store.fetchAgentDetail(agentId)
})

async function handleSkillDiscovery() {
  if (!store.currentAgent) return
  const result = await store.triggerSkillDiscovery(store.currentAgent.id)
  if (result) ElMessage.success('Skill发现完成')
}

async function handleDelete() {
  if (!store.currentAgent) return
  try {
    await ElMessageBox.confirm('确定移除该Agent？', '确认', { type: 'warning' })
    await store.deleteAgent(store.currentAgent.id)
    ElMessage.success('Agent已移除')
    router.push({ name: 'AgentList' })
  } catch {}
}

function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN')
}
</script>

<style lang="scss" scoped>
.agent-detail-view {
  &__header {
    display: flex;
    align-items: center;
    gap: $spacing-3;
    margin-bottom: $spacing-6;
    h2 { margin: 0; font-size: $font-size-2xl; font-weight: $font-weight-bold; }
  }
  &__gateway {
    display: flex;
    align-items: center;
    gap: $spacing-2;
  }
  &__status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    &.online { background: #67c23a; }
    &.offline { background: #909399; }
  }
}
</style>
