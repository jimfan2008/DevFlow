<template>
  <el-dialog
    v-model="visible"
    :title="title"
    :width="width"
    :close-on-click-modal="false"
    @closed="handleClosed"
  >
    <div class="confirm-dialog__body">
      <el-icon v-if="icon" :size="24" :class="`confirm-dialog__icon--${type}`">
        <WarningFilled v-if="type === 'warning'" />
        <InfoFilled v-else-if="type === 'info'" />
        <CircleCheckFilled v-else />
      </el-icon>
      <p class="confirm-dialog__message">{{ message }}</p>
    </div>
    <template #footer>
      <el-button @click="handleCancel" :disabled="loading">
        {{ cancelText }}
      </el-button>
      <el-button
        :type="buttonType"
        :loading="loading"
        @click="handleConfirm"
      >
        {{ confirmText }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { WarningFilled, InfoFilled, CircleCheckFilled } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
  type?: 'warning' | 'info' | 'success'
  width?: string
  loading?: boolean
}>(), {
  title: '确认操作',
  message: '确定执行此操作吗？',
  confirmText: '确定',
  cancelText: '取消',
  type: 'warning',
  width: '420px',
  loading: false,
})

const emit = defineEmits<{
  confirm: []
  cancel: []
  closed: []
}>()

const visible = ref(false)

const buttonType = computed(() => {
  if (props.type === 'warning') return 'danger'
  if (props.type === 'success') return 'success'
  return 'primary'
})

function open() {
  visible.value = true
}

function close() {
  visible.value = false
}

function handleConfirm() {
  emit('confirm')
}

function handleCancel() {
  emit('cancel')
  close()
}

function handleClosed() {
  emit('closed')
}

defineExpose({ open, close })
</script>

<style lang="scss" scoped>
.confirm-dialog {
  &__body {
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }

  &__icon--warning { color: $priority-high; }
  &__icon--info { color: $primary-color; }
  &__icon--success { color: $status-done; }

  &__message {
    margin: 0;
    font-family: $font-text;
    font-size: $body-size;
    font-weight: $body-weight;
    letter-spacing: $body-tracking;
    color: $ink;
    line-height: $body-leading;
  }
}
</style>
