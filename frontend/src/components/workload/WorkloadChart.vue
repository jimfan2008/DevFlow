<template>
  <div class="workload-chart" v-loading="loading">
    <div class="workload-chart__header">
      <h3>{{ title }}</h3>
      <div class="workload-chart__legend">
        <span class="workload-chart__legend-item">
          <span class="workload-chart__legend-color workload-chart__legend-color--todo" />
          待办
        </span>
        <span class="workload-chart__legend-item">
          <span class="workload-chart__legend-color workload-chart__legend-color--progress" />
          进行中
        </span>
        <span class="workload-chart__legend-item">
          <span class="workload-chart__legend-color workload-chart__legend-color--review" />
          审核
        </span>
        <span class="workload-chart__legend-item">
          <span class="workload-chart__legend-color workload-chart__legend-color--done" />
          已完成
        </span>
      </div>
    </div>

    <div class="workload-chart__summary" v-if="summary">
      <div class="workload-chart__stat">
        <span class="workload-chart__stat-value">{{ summary.total_tasks }}</span>
        <span class="workload-chart__stat-label">总任务</span>
      </div>
      <div class="workload-chart__stat">
        <span class="workload-chart__stat-value">{{ summary.total_members }}</span>
        <span class="workload-chart__stat-label">成员</span>
      </div>
      <div class="workload-chart__stat">
        <span class="workload-chart__stat-value">{{ summary.overloaded_members }}</span>
        <span class="workload-chart__stat-label">过载</span>
      </div>
      <div class="workload-chart__stat">
        <span class="workload-chart__stat-value">{{ summary.underloaded_members }}</span>
        <span class="workload-chart__stat-label">空闲</span>
      </div>
    </div>

    <div v-if="hasData">
      <div
        v-for="member in members"
        :key="member.user_id"
        class="workload-chart__member"
      >
        <div class="workload-chart__member-info">
          <div class="workload-chart__member-name">
            <el-avatar :size="24">{{ member.display_name?.charAt(0) }}</el-avatar>
            <span>{{ member.display_name }}</span>
          </div>
          <WorkloadBadge
            :overload="member.overload"
            :underload="member.underload"
            :completion-ratio="member.completion_ratio"
          />
        </div>

        <div class="workload-chart__bars">
          <div class="workload-chart__bar-group">
            <div
              class="workload-chart__bar workload-chart__bar--todo"
              :style="{ width: getBarWidth(member.tasks_by_status.todo, member.total_tasks) }"
            />
            <div
              class="workload-chart__bar workload-chart__bar--progress"
              :style="{ width: getBarWidth(member.tasks_by_status.in_progress, member.total_tasks) }"
            />
            <div
              class="workload-chart__bar workload-chart__bar--review"
              :style="{ width: getBarWidth(member.tasks_by_status.review, member.total_tasks) }"
            />
            <div
              class="workload-chart__bar workload-chart__bar--done"
              :style="{ width: getBarWidth(member.tasks_by_status.done, member.total_tasks) }"
            />
          </div>
          <span class="workload-chart__bar-total">{{ member.total_tasks }}</span>
        </div>

        <div class="workload-chart__hours" v-if="showHours">
          <span class="workload-chart__hours-bar">
            <span
              class="workload-chart__hours-fill"
              :style="{ width: getHoursWidth(member.completed_estimate_hours, member.total_estimate_hours) }"
            />
          </span>
          <span class="workload-chart__hours-text">
            {{ Math.round(member.completed_estimate_hours) }}/{{ Math.round(member.total_estimate_hours) }}h
          </span>
        </div>
      </div>
    </div>

    <EmptyState
      v-else
      type="default"
      title="暂无负载数据"
      :padding="40"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import EmptyState from '@/components/common/EmptyState.vue'
import WorkloadBadge from './WorkloadBadge.vue'
import type { WorkloadMember, WorkloadSummary } from '@/types/api'

const props = withDefaults(defineProps<{
  title?: string
  members?: WorkloadMember[]
  summary?: WorkloadSummary | null
  loading?: boolean
  showHours?: boolean
}>(), {
  title: '团队负载',
  members: () => [],
  summary: null,
  loading: false,
  showHours: true,
})

const hasData = computed(() => props.members.length > 0)

function getBarWidth(count: number, total: number): string {
  if (total === 0) return '0%'
  return `${(count / total) * 100}%`
}

function getHoursWidth(completed: number, total: number): string {
  if (total === 0) return '0%'
  return `${Math.min((completed / total) * 100, 100)}%`
}
</script>

<style lang="scss" scoped>
.workload-chart {
  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-4;

    h3 {
      margin: 0;
      font-family: $font-text;
      font-size: $body-strong-size;
      font-weight: $body-strong-weight;
      letter-spacing: $body-strong-tracking;
      color: $ink;
    }
  }

  &__legend {
    display: flex;
    gap: $spacing-sm;
  }

  &__legend-item {
    display: flex;
    align-items: center;
    gap: $spacing-xxs;
    font-size: $fine-print-size;
    color: $ink-muted-48;
  }

  &__legend-color {
    width: 10px;
    height: 10px;
    border-radius: 2px;

    &--todo { background: $status-todo; }
    &--progress { background: $status-in-progress; }
    &--review { background: $status-review; }
    &--done { background: $status-done; }
  }

  &__summary {
    display: flex;
    gap: $spacing-lg;
    margin-bottom: $spacing-4;
    padding-bottom: $spacing-4;
    border-bottom: 1px solid $hairline;
  }

  &__stat {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  &__stat-value {
    font-family: $font-display;
    font-size: $display-lg-size;
    font-weight: $display-lg-weight;
    letter-spacing: $display-lg-tracking;
    color: $ink;
  }

  &__stat-label {
    font-size: $caption-size;
    color: $ink-muted-48;
  }

  &__member {
    padding: $spacing-sm 0;
    border-bottom: 1px solid $hairline;
    &:last-child { border-bottom: none; }
  }

  &__member-info {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-xs;
  }

  &__member-name {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-family: $font-text;
    font-size: $body-strong-size;
    font-weight: $body-strong-weight;
    letter-spacing: $body-strong-tracking;
    color: $ink;
  }

  &__bars {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
  }

  &__bar-group {
    display: flex;
    height: 12px;
    flex: 1;
    border-radius: 6px;
    overflow: hidden;
    background: $canvas-parchment;
  }

  &__bar {
    height: 100%;
    transition: width 0.3s;

    &--todo { background: $status-todo; }
    &--progress { background: $status-in-progress; }
    &--review { background: $status-review; }
    &--done { background: $status-done; }
  }

  &__bar-total {
    font-size: $fine-print-size;
    color: $ink-muted-48;
    min-width: 24px;
    text-align: right;
  }

  &__hours {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    margin-top: $spacing-xxs;
  }

  &__hours-bar {
    flex: 1;
    height: 4px;
    background: $canvas-parchment;
    border-radius: 2px;
    overflow: hidden;
  }

  &__hours-fill {
    display: block;
    height: 100%;
    background: $primary;
    border-radius: 2px;
    transition: width 0.3s;
  }

  &__hours-text {
    font-size: $fine-print-size;
    color: $ink-muted-48;
    min-width: 60px;
    text-align: right;
  }
}
</style>
