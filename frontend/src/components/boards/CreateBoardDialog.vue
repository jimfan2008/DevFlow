<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑看板' : '创建看板'"
    width="520px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="80px"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="名称" prop="name">
        <el-input v-model="form.name" placeholder="看板名称" maxlength="50" />
      </el-form-item>
      <el-form-item label="描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          placeholder="看板描述（可选）"
          maxlength="200"
        />
      </el-form-item>
      <el-form-item v-if="!isEdit" label="初始列">
        <div class="create-board__columns">
          <div
            v-for="(col, idx) in form.columns"
            :key="idx"
            class="create-board__column-row"
          >
            <el-input
              v-model="col.name"
              placeholder="列名称"
              size="small"
              style="flex: 1"
            />
            <el-color-picker v-model="col.color" size="small" />
            <el-button
              :icon="Delete"
              text
              size="small"
              @click="removeColumn(idx)"
              :disabled="form.columns.length <= 1"
            />
          </div>
          <el-button text size="small" :icon="Plus" @click="addColumn">
            添加列
          </el-button>
        </div>
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
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Plus } from '@element-plus/icons-vue'
import { useBoardStore } from '@/stores/useBoardStore'
import type { BoardDetail } from '@/types/api'

const emit = defineEmits<{
  success: []
}>()

const boardStore = useBoardStore()
const visible = ref(false)
const submitting = ref(false)
const isEdit = ref(false)
const editBoardId = ref<string | null>(null)
const formRef = ref()

const defaultColumns = [
  { name: '待办', color: '#6b7280' },
  { name: '进行中', color: '#3b82f6' },
  { name: '已完成', color: '#10b981' },
]

const form = reactive({
  name: '',
  description: '',
  columns: JSON.parse(JSON.stringify(defaultColumns)),
})

const rules = {
  name: [
    { required: true, message: '请输入看板名称', trigger: 'blur' },
    { max: 50, message: '名称不超过50个字符', trigger: 'blur' },
  ],
}

function addColumn() {
  form.columns.push({ name: '', color: '#6b7280' })
}

function removeColumn(idx: number) {
  if (form.columns.length > 1) {
    form.columns.splice(idx, 1)
  }
}

function openForEdit(board: BoardDetail | null) {
  if (!board) return
  isEdit.value = true
  editBoardId.value = board.id
  form.name = board.name
  form.description = board.description
  visible.value = true
}

function open() {
  isEdit.value = false
  editBoardId.value = null
  form.name = ''
  form.description = ''
  form.columns = JSON.parse(JSON.stringify(defaultColumns))
  visible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value && editBoardId.value) {
      await boardStore.updateBoard(editBoardId.value, {
        name: form.name,
        description: form.description,
      })
      ElMessage.success('看板已更新')
    } else {
      await boardStore.createBoard({
        name: form.name,
        description: form.description,
        columns: form.columns.filter(c => c.name.trim()),
      })
      ElMessage.success('看板已创建')
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

<style lang="scss" scoped>
.create-board {
  &__columns {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
  }

  &__column-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}
</style>
