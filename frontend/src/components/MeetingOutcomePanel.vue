<template>
  <el-card shadow="never" class="outcome-panel">
    <template #header>
      <div class="outcome-panel__header">
        <span class="outcome-panel__title">
          <el-icon style="margin-right: 4px; color: #7c3aed;"><List /></el-icon>
          会议结果 - {{ outcome.meeting_topic }}
        </span>
        <span class="outcome-panel__date">{{ new Date().toLocaleDateString() }}</span>
      </div>
    </template>
    <div class="outcome-panel__body">
      <div v-if="outcome.decisions && outcome.decisions.length > 0" class="outcome-panel__section">
        <h4 class="outcome-panel__section-title">
          <el-icon style="color: #16a34a;"><CircleCheck /></el-icon>
          决议结论
        </h4>
        <el-timeline>
          <el-timeline-item
            v-for="(d, i) in outcome.decisions"
            :key="i"
            :timestamp="d.owner ? `Owner: ${d.owner}` : ''"
            placement="top"
            size="small"
          >
            {{ d.description }}
          </el-timeline-item>
        </el-timeline>
      </div>
      <div v-if="outcome.todos && outcome.todos.length > 0" class="outcome-panel__section">
        <h4 class="outcome-panel__section-title">
          <el-icon style="color: #2563eb;"><Document /></el-icon>
          待办任务
        </h4>
        <el-timeline>
          <el-timeline-item
            v-for="(t, i) in outcome.todos"
            :key="i"
            placement="top"
            size="small"
          >
            <div class="outcome-panel__todo-item">
              <span>{{ t.description }}</span>
              <div class="outcome-panel__todo-meta">
                <el-tag v-if="t.assignee" size="small" effect="plain" type="primary">{{ t.assignee }}</el-tag>
                <el-tag v-if="t.deadline" size="small" effect="plain" type="warning">截止: {{ t.deadline }}</el-tag>
              </div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
      <div v-if="outcome.risks && outcome.risks.length > 0" class="outcome-panel__section">
        <h4 class="outcome-panel__section-title">
          <el-icon style="color: #dc2626;"><WarningFilled /></el-icon>
          风险与规避
        </h4>
        <el-timeline>
          <el-timeline-item
            v-for="(r, i) in outcome.risks"
            :key="i"
            placement="top"
            size="small"
          >
            <div class="outcome-panel__risk-item">
              <span class="outcome-panel__risk-desc">{{ r.description }}</span>
              <span v-if="r.mitigation" class="outcome-panel__risk-mitigation">
                <el-icon style="color: #16a34a; margin: 0 4px;"><Right /></el-icon>
                {{ r.mitigation }}
              </span>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
      <div v-if="outcome.open_issues && outcome.open_issues.length > 0" class="outcome-panel__section">
        <h4 class="outcome-panel__section-title">
          <el-icon style="color: #d97706;"><QuestionFilled /></el-icon>
          遗留问题
        </h4>
        <el-timeline>
          <el-timeline-item
            v-for="(o, i) in outcome.open_issues"
            :key="i"
            placement="top"
            size="small"
          >
            <div class="outcome-panel__issue-item">
              <span>{{ o.description }}</span>
              <el-tag v-if="o.next_step" size="small" effect="plain" type="info">下一步: {{ o.next_step }}</el-tag>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
      <el-empty
        v-if="!outcome.decisions?.length && !outcome.todos?.length && !outcome.risks?.length && !outcome.open_issues?.length"
        description="暂无会议结果"
        :image-size="40"
      />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { List, CircleCheck, Document, WarningFilled, Right, QuestionFilled } from '@element-plus/icons-vue'
import type { MeetingOutcome } from '@/types'

defineProps<{
  outcome: MeetingOutcome
}>()
</script>

<style lang="scss" scoped>
.outcome-panel {
  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  &__title {
    display: flex;
    align-items: center;
    font-size: $font-size-sm;
    font-weight: $font-weight-semibold;
    color: #6d28d9;
  }

  &__date {
    font-size: $font-size-xs;
    color: $text-color-secondary;
  }

  &__body {
    padding: 0;
  }

  &__section {
    padding: $spacing-3;

    & + & {
      border-top: 1px solid $border-color-light;
    }
  }

  &__section-title {
    display: flex;
    align-items: center;
    gap: $spacing-1;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: $text-color-primary;
    margin: 0 0 $spacing-2 0;
  }

  &__todo-meta {
    display: flex;
    gap: $spacing-1;
    margin-top: $spacing-1;
  }

  &__risk-item {
    display: flex;
    flex-direction: column;
    gap: $spacing-1;
  }

  &__risk-desc {
    color: #b91c1c;
  }

  &__risk-mitigation {
    display: inline-flex;
    align-items: center;
    color: #16a34a;
    font-size: $font-size-xs;
  }

  &__issue-item {
    display: flex;
    flex-direction: column;
    gap: $spacing-1;
  }
}
</style>