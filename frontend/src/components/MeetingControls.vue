<template>
  <el-dialog
    v-model="visible"
    title="开始会议"
    width="520px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="会议类型" prop="meetingType">
        <el-select v-model="form.meetingType" placeholder="选择会议类型" style="width: 100%">
          <el-option value="requirement_review" label="需求评审会" />
          <el-option value="tech_solution" label="技术方案讨论会" />
          <el-option value="daily_standup" label="每日站会 / 进度同步会" />
          <el-option value="incident_postmortem" label="故障复盘会" />
        </el-select>
      </el-form-item>
      <el-form-item label="讨论议题" prop="topic">
        <el-input v-model="form.topic" placeholder="输入讨论议题" maxlength="100" />
      </el-form-item>
      <el-form-item label="主持 Agent" prop="hostAgent">
        <el-select v-model="form.hostAgent" placeholder="选择主持 agent" style="width: 100%">
          <el-option v-for="member in members" :key="member" :label="member" :value="member" />
        </el-select>
      </el-form-item>
      <el-form-item label="预计时长" prop="durationMinutes">
        <el-input-number v-model="form.durationMinutes" :min="10" :max="180" />
        <span class="member-list__duration-label">分钟</span>
      </el-form-item>
      <el-form-item label="会前物料" prop="preMaterials">
        <el-input
          v-model="form.preMaterials"
          type="textarea"
          :rows="2"
          placeholder="PRD/原型/方案/接口/bug列表链接等（可多行）"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button
        type="primary"
        :disabled="!form.topic || !form.hostAgent"
        @click="handleSubmit"
      >开始会议</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'

const props = defineProps<{
  groupId: string
  members: string[]
}>()

const emit = defineEmits<{
  close: []
  start: [data: { topic: string; hostAgent: string; meetingType: string; durationMinutes: number; preMaterials: string }]
}>()

const visible = ref(true)
const formRef = ref()

const form = reactive({
  meetingType: 'tech_solution',
  topic: '',
  hostAgent: '',
  durationMinutes: 45,
  preMaterials: '',
})

const rules = {
  topic: [
    { required: true, message: '请输入讨论议题', trigger: 'blur' },
    { max: 100, message: '议题不超过100个字符', trigger: 'blur' },
  ],
  hostAgent: [
    { required: true, message: '请选择主持 agent', trigger: 'change' },
  ],
}

function handleSubmit() {
  if (!form.topic || !form.hostAgent) return
  emit('start', {
    topic: form.topic,
    hostAgent: form.hostAgent,
    meetingType: form.meetingType,
    durationMinutes: form.durationMinutes,
    preMaterials: form.preMaterials,
  })
}

function handleClose() {
  emit('close')
}
</script>

<style lang="scss" scoped>
.member-list__duration-label {
  margin-left: $spacing-2;
  font-size: $font-size-sm;
  color: $text-color-secondary;
}
</style>