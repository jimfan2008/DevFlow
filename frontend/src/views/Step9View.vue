<script setup lang="ts">
import { useWorkflowStep } from '@/composables/useWorkflowStep'
import WorkflowStepBase from '@/components/WorkflowStepBase.vue'

const props = defineProps<{ projectId: string }>()

const stepNumber = 9

const {
  projectName, loading, executing, error, stageLog, liveContent,
  streamStatus, haimeiPrompt, showPrompt, stepStatus,
  prevStep, nextStep, stepName, statusLabelMap, statusTagType,
  handleExecute, handleGoPrev, handleGoNext, goBack,
} = useWorkflowStep({ projectId: props.projectId, stepNumber })
</script>

<template>
<WorkflowStepBase
  :project-id="projectId"
  :step-number="stepNumber"
  :project-name="projectName"
  :loading="loading"
  :executing="executing"
  :error="error"
  :step-status="stepStatus"
  :step-name="stepName"
  :prev-step="prevStep"
  :next-step="nextStep"
  :stage-log="stageLog"
  :live-content="liveContent"
  :stream-status="streamStatus"
  :haimei-prompt="haimeiPrompt"
  :show-prompt="showPrompt"
  :status-label-map="statusLabelMap"
  :status-tag-type="statusTagType"
  @execute="handleExecute"
  @go-prev="handleGoPrev"
  @go-next="handleGoNext"
  @go-back="goBack"
  @toggle-prompt="showPrompt = !showPrompt"
  @close-error="error = ''"
/>
</template>
