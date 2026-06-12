<template>
  <div class="agent-list-view">
    <div class="agent-list-view__header">
      <h2 class="agent-list-view__title">Agent管理</h2>
      <div class="agent-list-view__actions">
        <el-button @click="handleProfileScan" :loading="scanLoading">Profile扫描</el-button>
        <el-select v-model="agentTypeFilter" placeholder="类型筛选" style="width: 140px" clearable @change="handleFilterChange">
          <el-option label="全部" value="" />
          <el-option label="Hermes Agent" value="hermes" />
          <el-option label="编程Agent" value="programming" />
        </el-select>
      </div>
    </div>

    <div v-loading="store.loading" class="agent-list-view__grid">
      <el-card v-for="agent in store.agents" :key="agent.id" class="agent-list-view__card" shadow="never" @click="goToDetail(agent.id)">
        <template #header>
          <div class="agent-list-view__card-header">
            <span class="agent-list-view__card-name">{{ agent.name }}</span>
            <el-tag :type="agent.status === 'online' ? 'success' : agent.status === 'busy' ? 'warning' : 'info'" size="small" effect="dark">
              {{ agent.status === 'online' ? '在线' : agent.status === 'busy' ? '忙碌' : '离线' }}
            </el-tag>
          </div>
        </template>
        <div class="agent-list-view__card-body">
          <el-tag size="small" :type="agent.agent_type === 'hermes' ? '' : 'success'">{{ agent.agent_type === 'hermes' ? 'Hermes' : '编程' }}</el-tag>
          <span v-if="agent.discovered_by" class="agent-list-view__discovered">发现者: {{ agent.discovered_by }}</span>
          <span v-if="agent.version" class="agent-list-view__version">v{{ agent.version }}</span>
        </div>
        <div class="agent-list-view__card-actions">
          <el-button v-if="agent.agent_type === 'hermes'" size="small" type="primary" plain @click.stop="handleSkillDiscovery(agent.id)">Skill发现</el-button>
          <el-button size="small" type="danger" plain @click.stop="handleDeleteAgent(agent)">删除</el-button>
        </div>
      </el-card>
    </div>

    <div v-if="!store.loading && store.agents.length === 0" class="agent-list-view__empty">
      <el-empty description="暂无Agent" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAgentStore } from '@/stores/useAgentStore'

const router = useRouter()
const store = useAgentStore()
const agentTypeFilter = ref('')
const scanLoading = ref(false)

onMounted(() => {
  store.fetchAgents()
})

function handleFilterChange() {
  store.fetchAgents(agentTypeFilter.value || undefined)
}

function goToDetail(agentId: string) {
  router.push({ name: 'AgentDetail', params: { agentId } })
}

async function handleProfileScan() {
  scanLoading.value = true
  const result = await store.triggerProfileScan()
  scanLoading.value = false
  if (result) {
    ElMessage.success('Profile扫描完成')
  }
}

async function handleSkillDiscovery(agentId: string) {
  const result = await store.triggerSkillDiscovery(agentId)
  if (result) {
    ElMessage.success('Skill发现完成')
  }
}

async function handleDeleteAgent(agent: any) {
  try {
    await ElMessageBox.confirm(`确定删除Agent"${agent.name}"？`, '删除确认', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
    const ok = await store.deleteAgent(agent.id)
    if (ok) ElMessage.success('已删除')
  } catch {}
}
</script>

<style lang="scss" scoped>
.agent-list-view {
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
  &__actions {
    display: flex;
    gap: $spacing-xs;
  }
  &__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: $spacing-lg;
  }
  &__card {
    cursor: pointer;
    border-radius: $radius-lg;
    &-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    &-name {
      font-family: $font-text;
      font-size: $body-strong-size;
      font-weight: $body-strong-weight;
      letter-spacing: $body-strong-tracking;
    }
    &-body {
      display: flex;
      align-items: center;
      gap: $spacing-xs;
      margin-bottom: $spacing-xs;
    }
    &-actions {
      display: flex;
      gap: $spacing-xs;
    }
  }
  &__discovered, &__version {
    font-size: $caption-size;
    color: $ink-muted-48;
  }
  &__empty {
    display: flex;
    justify-content: center;
    padding: 60px 0;
  }
}
</style>
