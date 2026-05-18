<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑任务' : '创建任务'"
    width="540px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="80px"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="标题" prop="title">
        <el-input v-model="form.title" placeholder="任务标题" maxlength="100" />
      </el-form-item>
      <el-form-item label="描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          placeholder="任务描述（可选）"
        />
      </el-form-item>
      <el-form-item label="所属列" prop="column_id">
        <el-select v-model="form.column_id" placeholder="选择列" style="width: 100%">
          <el-option
            v-for="col in columns"
            :key="col.id"
            :label="col.name"
            :value="col.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="优先级" prop="priority">
        <el-select v-model="form.priority" placeholder="选择优先级" style="width: 100%">
          <el-option label="低" value="low" />
          <el-option label="中" value="medium" />
          <el-option label="高" value="high" />
          <el-option label="紧急" value="urgent" />
        </el-select>
      </el-form-item>
      <el-form-item label="负责人" prop="assignee_id">
        <div class="task-form__assignee-row">
          <el-select
            v-model="form.assignee_id"
            placeholder="选择负责人"
            clearable
            filterable
            style="flex: 1"
          >
            <el-option
              v-for="user in userList"
              :key="user.id"
              :label="user.display_name"
              :value="user.id"
            />
          </el-select>
          <el-tooltip content="Agent 基于负载最低原则自动分配" placement="top">
            <el-button
              :icon="Aim"
              :loading="autoAssigning"
              @click="handleAutoAssign"
              :disabled="!createdTaskId && !isEdit"
            >
              Agent分配
            </el-button>
          </el-tooltip>
          <div v-if="autoAssignResult" class="task-form__agent-result">
            <el-tag type="success" size="small" effect="light">
              Agent已分配: {{ autoAssignResult }}
            </el-tag>
          </div>
        </div>
      </el-form-item>
      <el-form-item label="截止日期" prop="due_date">
        <el-date-picker
          v-model="form.due_date"
          type="date"
          placeholder="选择日期"
          style="width: 100%"
          value-format="YYYY-MM-DD"
        />
      </el-form-item>
      <el-form-item label="标签" prop="tags">
        <el-select
          v-model="form.tags"
          multiple
          allow-create
          filterable
          placeholder="输入标签后回车"
          style="width: 100%"
        >
          <el-option
            v-for="tag in existingTags"
            :key="tag"
            :label="tag"
            :value="tag"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="预估工时" prop="estimate_hours">
        <el-input-number
          v-model="form.estimate_hours"
          :min="0"
          :max="999"
          :step="0.5"
          placeholder="小时"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ isEdit ? '保存' : '创建' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim } from '@element-plus/icons-vue'
import { useBoardStore } from '@/stores/useBoardStore'
import { useTaskStore } from '@/stores/useTaskStore'
import { userApi, workloadApi } from '@/api'
import type { UserListItem } from '@/types/api'

const props = withDefaults(defineProps<{
  boardId?: string
  initialColumnId?: string
  taskId?: string
}>(), {
  boardId: '',
  initialColumnId: '',
  taskId: '',
})

const emit = defineEmits<{
  success: []
}>()

const boardStore = useBoardStore()
const taskStore = useTaskStore()
const visible = ref(false)
const submitting = ref(false)
const isEdit = ref(false)
const formRef = ref()
const userList = ref<UserListItem[]>([])
const autoAssigning = ref(false)
const createdTaskId = ref<string | null>(null)
const autoAssignResult = ref<string | null>(null)

const columns = computed(() => boardStore.columns)
const existingTags = ref<string[]>([])

const form = reactive({
  title: '',
  description: '',
  column_id: '',
  priority: 'medium' as 'low' | 'medium' | 'high' | 'urgent',
  assignee_id: null as string | null,
  due_date: null as string | null,
  tags: [] as string[],
  estimate_hours: null as number | null,
})

const rules = {
  title: [
    { required: true, message: '请输入任务标题', trigger: 'blur' },
    { max: 100, message: '标题不超过100个字符', trigger: 'blur' },
  ],
  column_id: [{ required: true, message: '请选择所属列', trigger: 'change' }],
}

onMounted(async () => {
  try {
    const res = await userApi.list({ page_size: 100 })
    if (res.data) {
      userList.value = res.data
    }
  } catch {
    // user list is optional for task creation
  }
})

function open() {
  isEdit.value = false
  resetForm()
  visible.value = true
}

function openForEdit(taskId: string) {
  isEdit.value = true
  visible.value = true
  loadTask(taskId)
}

async function loadTask(taskId: string) {
  try {
    const res = await taskStore.fetchDetail(taskId)
    if (taskStore.currentTask) {
      const t = taskStore.currentTask
      form.title = t.title
      form.description = t.description || ''
      form.column_id = t.column_id
      form.priority = t.priority
      form.assignee_id = t.assignee_id
      form.due_date = t.due_date
      form.tags = [...t.tags]
      form.estimate_hours = t.estimate_hours ?? null
    }
  } catch (e: any) {
    ElMessage.error(e.message || '加载任务失败')
  }
}

function resetForm() {
  form.title = ''
  form.description = ''
  form.column_id = props.initialColumnId || ''
  if (!form.column_id && columns.value.length > 0) {
    form.column_id = columns.value[0].id
  }
  form.priority = 'medium'
  form.assignee_id = null
  form.due_date = null
  form.tags = []
  form.estimate_hours = null
  createdTaskId.value = null
  autoAssignResult.value = null
}

async function handleAutoAssign() {
  const taskId = createdTaskId.value || (isEdit.value ? props.taskId : null)
  if (!taskId) return
  autoAssigning.value = true
  autoAssignResult.value = null
  try {
    const res = await workloadApi.autoAssign(taskId)
    if (res.data?.assigned_to) {
      form.assignee_id = res.data.assigned_to.id
      autoAssignResult.value = res.data.assigned_to.display_name
      ElMessage.success(`Agent已将任务分配给 ${res.data.assigned_to.display_name}`)
    }
  } catch (e: any) {
    ElMessage.error(e.message || 'Agent分配失败')
  } finally {
    autoAssigning.value = false
  }
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value && props.taskId) {
      await taskStore.updateTask(props.taskId, {
        title: form.title,
        description: form.description || undefined,
        column_id: form.column_id,
        priority: form.priority,
        assignee_id: form.assignee_id,
        due_date: form.due_date,
        tags: form.tags.length > 0 ? form.tags : undefined,
        estimate_hours: form.estimate_hours,
      })
      ElMessage.success('任务已更新')
    } else {
      const res = await taskStore.createTask({
        board_id: props.boardId,
        column_id: form.column_id,
        title: form.title,
        description: form.description || undefined,
        priority: form.priority,
        assignee_id: form.assignee_id,
        due_date: form.due_date,
        tags: form.tags.length > 0 ? form.tags : undefined,
        estimate_hours: form.estimate_hours,
      })
      if (res.data?.id) {
        createdTaskId.value = res.data.id
      }
      ElMessage.success('任务已创建')
    }
    visible.value = false
    emit('success')
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

defineExpose({ open, openForEdit })
</script>
