<template>
  <el-drawer
    v-model="visible"
    :title="task?.title || '任务详情'"
    size="520px"
    :close-on-click-modal="false"
    @open="handleOpen"
    @closed="handleClosed"
  >
    <template v-if="task" v-loading="loading">
      <div class="task-detail">
        <div class="task-detail__field">
          <label>状态</label>
          <StatusBadge :status="task.status" size="default" />
        </div>
        <div class="task-detail__field">
          <label>优先级</label>
          <PriorityBadge :priority="task.priority" size="default" />
        </div>
        <div class="task-detail__field" v-if="task.assignee">
          <label>负责人</label>
          <div class="task-detail__assignee">
            <el-avatar :size="24">{{ task.assignee.display_name?.charAt(0) }}</el-avatar>
            <span>{{ task.assignee.display_name }}</span>
          </div>
        </div>
        <div class="task-detail__field" v-if="task.due_date">
          <label>截止日期</label>
          <span :class="{ 'is-overdue': task.due_overdue }">
            {{ formatDate(task.due_date) }}
          </span>
        </div>
        <div class="task-detail__field">
          <label>创建者</label>
          <span>{{ task.creator.display_name }}</span>
        </div>

        <el-divider />

        <div class="task-detail__section">
          <h4>描述</h4>
          <p class="task-detail__description" v-if="task.description">
            {{ task.description }}
          </p>
          <EmptyState v-else type="default" title="暂无描述" :padding="20" />
        </div>

        <el-divider />

        <div class="task-detail__section">
          <h4>评论 ({{ task.comments?.length || 0 }})</h4>
          <div class="task-detail__comments" v-if="task.comments && task.comments.length > 0">
            <div v-for="comment in task.comments" :key="comment.id" class="task-detail__comment">
              <div class="task-detail__comment-header">
                <el-avatar :size="20">{{ comment.user.display_name?.charAt(0) }}</el-avatar>
                <span class="task-detail__comment-user">{{ comment.user.display_name }}</span>
                <span class="task-detail__comment-time">{{ formatDate(comment.created_at) }}</span>
              </div>
              <p class="task-detail__comment-body">{{ comment.content }}</p>
            </div>
          </div>
          <EmptyState v-else type="default" title="暂无评论" :padding="20" />

          <div class="task-detail__add-comment">
            <el-input
              v-model="newComment"
              type="textarea"
              :rows="2"
              placeholder="输入评论..."
            />
            <el-button
              type="primary"
              size="small"
              :loading="commentLoading"
              :disabled="!newComment.trim()"
              @click="handleAddComment"
              style="margin-top: 8px"
            >
              发表评论
            </el-button>
          </div>
        </div>

        <el-divider />

        <div class="task-detail__section">
          <h4>依赖关系</h4>
          <TaskDependencyList
            :task-id="task.id"
            :predecessors="task.predecessors"
            :successors="task.successors"
          />
        </div>
      </div>
    </template>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button type="primary" @click="handleEdit">编辑</el-button>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useTaskStore } from '@/stores/useTaskStore'
import { useCommentStore } from '@/composables/useCommentStore'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import PriorityBadge from '@/components/ui/PriorityBadge.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import TaskDependencyList from './TaskDependencyList.vue'
import { format } from 'date-fns'

const props = withDefaults(defineProps<{
  taskId?: string
  modelValue?: boolean
}>(), {
  taskId: '',
  modelValue: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  edit: [taskId: string]
}>()

const taskStore = useTaskStore()
const commentStore = useCommentStore()
const visible = ref(props.modelValue)
const loading = ref(false)
const commentLoading = ref(false)
const newComment = ref('')
const task = computed(() => taskStore.currentTask)

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

async function handleOpen() {
  if (props.taskId) {
    loading.value = true
    try {
      await taskStore.fetchDetail(props.taskId)
    } catch (e: any) {
      ElMessage.error(e.message || '获取任务详情失败')
    } finally {
      loading.value = false
    }
  }
}

function handleClosed() {
  taskStore.clearCurrentTask()
}

async function handleAddComment() {
  if (!newComment.value.trim() || !props.taskId) return
  commentLoading.value = true
  try {
    await taskStore.addComment(props.taskId, newComment.value.trim())
    newComment.value = ''
    ElMessage.success('评论已添加')
  } catch (e: any) {
    ElMessage.error(e.message || '添加评论失败')
  } finally {
    commentLoading.value = false
  }
}

function handleEdit() {
  if (props.taskId) {
    emit('edit', props.taskId)
  }
}

function formatDate(dateStr: string): string {
  try {
    return format(new Date(dateStr), 'yyyy-MM-dd HH:mm')
  } catch {
    return dateStr
  }
}
</script>

<style lang="scss" scoped>
.task-detail {
  &__field {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    margin-bottom: $spacing-sm;

    label {
      width: 70px;
      font-family: $font-text;
      font-size: $body-size;
      color: $ink-muted-48;
      flex-shrink: 0;
    }

    .is-overdue { color: $status-blocked; }
  }

  &__assignee {
    display: flex;
    align-items: center;
    gap: $spacing-xxs;
  }

  &__section {
    h4 {
      margin: 0 0 $spacing-sm;
      font-family: $font-text;
      font-size: $body-strong-size;
      font-weight: $body-strong-weight;
      letter-spacing: $body-strong-tracking;
      color: $ink;
    }
  }

  &__description {
    font-family: $font-text;
    font-size: $body-size;
    font-weight: $body-weight;
    letter-spacing: $body-tracking;
    color: $ink;
    line-height: $body-leading;
    white-space: pre-wrap;
  }

  &__comment {
    margin-bottom: $spacing-sm;
    padding: $spacing-xs;
    background: $canvas-parchment;
    border-radius: $radius-sm;
  }

  &__comment-header {
    display: flex;
    align-items: center;
    gap: $spacing-xxs;
    margin-bottom: $spacing-xxs;
  }

  &__comment-user {
    font-family: $font-text;
    font-size: $body-strong-size;
    font-weight: $body-strong-weight;
    letter-spacing: $body-strong-tracking;
    color: $ink;
  }

  &__comment-time {
    font-size: $fine-print-size;
    color: $ink-muted-48;
    margin-left: auto;
  }

  &__comment-body {
    margin: $spacing-xxs 0 0;
    font-size: $body-size;
    color: $ink;
    white-space: pre-wrap;
  }

  &__add-comment {
    margin-top: $spacing-sm;
  }
}
</style>
