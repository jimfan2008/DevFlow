<template>
  <div class="skill-view">
    <div class="skill-view__header">
      <h2 class="skill-view__title">Hermes Skill管理</h2>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="状态概览" name="overview">
        <div v-loading="store.loading" class="skill-view__grid">
          <el-card v-for="skill in store.skills" :key="skill.id" shadow="never" class="skill-view__card">
            <template #header>
              <div class="skill-view__card-header">
                <span>{{ skill.name }}</span>
                <el-tag :type="skillStatusType(skill.status)" size="small">{{ skillStatusLabel(skill.status) }}</el-tag>
              </div>
            </template>
            <div class="skill-view__card-body">
              <div class="skill-view__status-row">
                <span>状态:</span>
                <el-steps :active="skillStepActive(skill.status)" finish-status="success" simple size="small">
                  <el-step title="空闲" />
                  <el-step title="发现" />
                  <el-step title="对接" />
                  <el-step title="执行" />
                </el-steps>
              </div>
              <div v-if="skill.paired_agent_id" class="skill-view__paired">
                已对接Agent: {{ skill.paired_agent_id }}
                <el-tag :type="skill.channel_status === 'connected' ? 'success' : 'danger'" size="small">
                  {{ skill.channel_status === 'connected' ? '通道正常' : '通道异常' }}
                </el-tag>
              </div>
            </div>
          </el-card>
        </div>
        <el-empty v-if="!store.loading && store.skills.length === 0" description="暂无Skill" />
      </el-tab-pane>

      <el-tab-pane label="发现编程Agent" name="discover">
        <el-table :data="store.skills" stripe v-loading="store.loading">
          <el-table-column prop="name" label="Skill名称" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="skillStatusType(row.status)" size="small">{{ skillStatusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click="handleDiscover(row.id)" :disabled="row.status === 'executing'">发现Agent</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="对接编程Agent" name="pair">
        <el-table :data="store.skills" stripe v-loading="store.loading">
          <el-table-column prop="name" label="Skill名称" />
          <el-table-column label="通信通道" width="120">
            <template #default="{ row }">
              <el-tag v-if="row.channel_status" :type="row.channel_status === 'connected' ? 'success' : 'danger'" size="small">
                {{ row.channel_status === 'connected' ? '已连接' : row.channel_status === 'error' ? '错误' : '断开' }}
              </el-tag>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="对接Agent" width="160">
            <template #default="{ row }">{{ row.paired_agent_id || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button size="small" type="success" @click="showPairDialog(row)" :disabled="!row.paired_agent_id && row.status === 'idle'">对接Agent</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="分配子任务" name="assign">
        <el-table :data="store.skills.filter((s: any) => s.paired_agent_id)" stripe v-loading="store.loading">
          <el-table-column prop="name" label="Skill名称" />
          <el-table-column label="已对接Agent">
            <template #default="{ row }">{{ row.paired_agent_id }}</template>
          </el-table-column>
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button size="small" type="warning" @click="showAssignDialog(row)">分配任务</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="执行历史" name="history">
        <el-table :data="store.executionHistory" stripe v-loading="store.loading">
          <el-table-column prop="skill_id" label="Skill" width="120" />
          <el-table-column prop="task_id" label="任务ID" width="120" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="started_at" label="开始时间" width="180">
            <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="pairDialogVisible" title="对接编程Agent" width="400px">
      <el-form label-width="80px">
        <el-form-item label="Agent ID">
          <el-input v-model="pairForm.agentId" placeholder="输入编程Agent ID" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pairDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="store.loading" @click="handlePair">确认对接</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="assignDialogVisible" title="分配子任务" width="400px">
      <el-form label-width="80px">
        <el-form-item label="任务 ID">
          <el-input v-model="assignForm.taskId" placeholder="输入任务ID" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="store.loading" @click="handleAssign">确认分配</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useSkillStore } from '@/stores/useSkillStore'
import type { Skill } from '@/types/api'

const store = useSkillStore()
const activeTab = ref('overview')
const pairDialogVisible = ref(false)
const assignDialogVisible = ref(false)
const pairForm = ref({ skillId: '', agentId: '' })
const assignForm = ref({ skillId: '', taskId: '' })

onMounted(() => {
  store.fetchSkills()
})

watch(activeTab, (tab) => {
  if (tab === 'history') {
    store.fetchExecutionHistory()
  }
})

function skillStatusLabel(status: string) {
  const map: Record<string, string> = { idle: '空闲', discovering: '发现中', pairing: '对接中', executing: '执行中' }
  return map[status] || status
}

function skillStatusType(status: string) {
  const map: Record<string, string> = { idle: 'info', discovering: '', pairing: 'warning', executing: 'success' }
  return (map[status] || 'info') as any
}

function skillStepActive(status: string) {
  const map: Record<string, number> = { idle: 0, discovering: 1, pairing: 2, executing: 3 }
  return map[status] ?? 0
}

async function handleDiscover(skillId: string) {
  const result = await store.discoverAgents(skillId)
  if (result.length > 0) ElMessage.success(`发现 ${result.length} 个编程Agent`)
  else ElMessage.info('未发现新的编程Agent')
}

function showPairDialog(skill: Skill) {
  pairForm.value = { skillId: skill.id, agentId: skill.paired_agent_id || '' }
  pairDialogVisible.value = true
}

async function handlePair() {
  await store.pairAgent(pairForm.value.skillId, pairForm.value.agentId)
  pairDialogVisible.value = false
  ElMessage.success('对接成功')
}

function showAssignDialog(skill: Skill) {
  assignForm.value = { skillId: skill.id, taskId: '' }
  assignDialogVisible.value = true
}

async function handleAssign() {
  if (!assignForm.value.taskId) return ElMessage.warning('请输入任务ID')
  await store.assignTask(assignForm.value.skillId, assignForm.value.taskId)
  assignDialogVisible.value = false
  ElMessage.success('任务已分配')
}

function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN')
}
</script>

<style lang="scss" scoped>
.skill-view {
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
  &__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: $spacing-lg;
  }
  &__card {
    border-radius: $radius-lg;
    &-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    &-body {
      display: flex;
      flex-direction: column;
      gap: $spacing-xs;
    }
  }
  &__status-row {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    span { font-size: $caption-size; color: $ink-muted-48; white-space: nowrap; }
  }
  &__paired {
    font-size: $caption-size;
    color: $ink-muted-48;
    display: flex;
    align-items: center;
    gap: $spacing-xs;
  }
}
</style>
