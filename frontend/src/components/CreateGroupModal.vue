<template>
  <el-dialog
    v-model="visible"
    title="创建群组"
    width="500px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form :model="form" label-width="100px">
      <el-form-item label="群组名称" required>
        <el-input v-model="form.name" placeholder="输入群组名称" maxlength="100" show-word-limit />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选：群组描述" />
      </el-form-item>
      <el-form-item label="选择Agent">
        <el-select v-model="form.members" multiple placeholder="选择要加入的Agent（可选）" style="width: 100%">
          <el-option
            v-for="agent in agents"
            :key="agent.name"
            :label="`${agent.name}${agent.is_running ? ' (在线)' : ' (离线)'}`"
            :value="agent.name"
            :disabled="!agent.is_running"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="loading" :disabled="!form.name.trim()" @click="handleCreate">创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { apiClient } from '@/api'
import type { GroupInfo } from '@/types'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{
  'update:visible': [val: boolean]
  created: [group: GroupInfo]
}>()

const visible = computed({
  get: () => props.visible,
  set: (val: boolean) => emit('update:visible', val),
})

const loading = ref(false)
const agents = ref<any[]>([])
const form = ref({
  name: '',
  description: '',
  members: [] as string[],
})

onMounted(() => {
  fetchAgents()
})

watch(() => props.visible, (val) => {
  if (val) {
    fetchAgents()
    form.value = { name: '', description: '', members: [] }
  }
})

async function fetchAgents() {
  try {
    const res = await apiClient.get('/profiles') as any
    const profiles = res?.data?.profiles || res?.profiles || []
    agents.value = profiles
  } catch (e) {
    console.error('Error fetching agents:', e)
  }
}

async function handleCreate() {
  if (!form.value.name.trim()) return
  loading.value = true
  try {
    const res = await apiClient.post('/groups', {
      name: form.value.name.trim(),
      description: form.value.description,
      members: form.value.members,
    }) as any
    const group = res?.data?.group || res?.data || res
    if (group?.id) {
      ElMessage.success('群组创建成功')
      emit('created', group as GroupInfo)
    }
  } catch (e: any) {
    ElMessage.error(e.message || '创建群组失败')
  } finally {
    loading.value = false
  }
}

function handleClose() {
  emit('update:visible', false)
}
</script>