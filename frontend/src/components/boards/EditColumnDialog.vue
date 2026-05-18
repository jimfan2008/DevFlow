<template>
  <el-dialog
    v-model="visible"
    :title="isCreate ? '新建列' : '编辑列'"
    width="400px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="60px"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="名称" prop="name">
        <el-input v-model="form.name" placeholder="列名称" maxlength="30" />
      </el-form-item>
      <el-form-item label="颜色" prop="color">
        <el-color-picker v-model="form.color" />
      </el-form-item>
      <el-form-item label="排序" prop="position">
        <el-input-number v-model="form.position" :min="0" :max="99" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ isCreate ? '创建' : '保存' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useBoardStore } from '@/stores/useBoardStore'
import type { BoardColumn } from '@/types/api'

const props = defineProps<{
  boardId: string
}>()

const emit = defineEmits<{
  success: []
}>()

const boardStore = useBoardStore()
const visible = ref(false)
const submitting = ref(false)
const isCreate = ref(false)
const editColumnId = ref<string | null>(null)
const formRef = ref()

const form = reactive({
  name: '',
  color: '#6b7280',
  position: 0,
})

const rules = {
  name: [
    { required: true, message: '请输入列名称', trigger: 'blur' },
    { max: 30, message: '名称不超过30个字符', trigger: 'blur' },
  ],
}

function openForCreate() {
  isCreate.value = true
  editColumnId.value = null
  form.name = ''
  form.color = '#6b7280'
  form.position = 0
  visible.value = true
}

function openForEdit(column: BoardColumn) {
  isCreate.value = false
  editColumnId.value = column.id
  form.name = column.name
  form.color = column.color
  form.position = column.position
  visible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isCreate.value) {
      await boardStore.createColumn(props.boardId, {
        name: form.name,
        color: form.color,
        position: form.position,
      })
      ElMessage.success('列已创建')
    } else if (editColumnId.value) {
      await boardStore.updateColumn(props.boardId, editColumnId.value, {
        name: form.name,
        color: form.color,
        position: form.position,
      })
      ElMessage.success('列已更新')
    }
    visible.value = false
    emit('success')
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

defineExpose({ openForCreate, openForEdit })
</script>
