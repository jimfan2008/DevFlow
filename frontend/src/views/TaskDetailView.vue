<template>
  <div class="task-detail-view" v-loading="loading">
    <div class="task-detail-view__header">
      <el-button text :icon="ArrowLeft" @click="goBack">
        返回看板
      </el-button>
    </div>

    <template v-if="task">
      <div class="task-detail-view__main">
        <div class="task-detail-view__content">
          <div class="task-detail-view__title-section">
            <h1 class="task-detail-view__title">{{ task.title }}</h1>
            <div class="task-detail-view__status-bar">
              <StatusBadge :status="task.status" size="default" />
              <PriorityBadge :priority="task.priority" size="default" />
              <template v-if="task.blocked">
                <el-tag type="danger" effect="light" size="small">阻塞</el-tag>
              </template>
            </div>
          </div>

          <el-divider />

          <div class="task-detail-view__info">
            <div class="task-detail-view__info-item">
              <label>负责人</label>
              <span v-if="task.assignee">{{ task.assignee.display_name }}</span>
              <span v-else class="task-detail-view__na">未指派</span>
            </div>
            <div class="task-detail-view__info-item">
              <label>创建者</label>
              <span>{{ task.creator.display_name }}</span>
            </div>
            <div class="task-detail-view__info-item">
              <label>截止日期</label>
              <span v-if="task.due_date" :class="{ 'is-overdue': task.due_overdue }">
                {{ formatDate(task.due_date) }}
              </span>
              <span v-else class="task-detail-view__na">未设置</span>
            </div>
            <div class="task-detail-view__info-item">
              <label>预估工时</label>
              <span v-if="task.estimate_hours">{{ task.estimate_hours }}h</span>
              <span v-else class="task-detail-view__na">未设置</span>
            </div>
            <div class="task-detail-view__info-item" v-if="task.tags && task.tags.length > 0">
              <label>标签</label>
              <div class="task-detail-view__tags">
                <el-tag v-for="tag in task.tags" :key="tag" size="small">{{ tag }}</el-tag>
              </div>
            </div>
            <div class="task-detail-view__info-item">
              <label>创建时间</label>
              <span>{{ formatDate(task.created_at) }}</span>
            </div>
            <div class="task-detail-view__info-item">
              <label>更新时间</label>
              <span>{{ formatDate(task.updated_at) }}</span>
            </div>
          </div>

          <el-divider />

          <div class="task-detail-view__section">
            <h3>描述</h3>
            <p class="task-detail-view__description" v-if="task.description">
              {{ task.description }}
            </p>
            <EmptyState v-else type="default" title="暂无描述" :padding="20" />
          </div>

          <el-divider />

          <div class="task-detail-view__section">
            <h3>评论（{{ task.comments?.length || 0 }}）</h3>
            <div class="task-detail-view__comments" v-if="task.comments && task.comments.length > 0">
              <div v-for="comment in task.comments" :key="comment.id" class="task-detail-view__comment">
                <div class="task-detail-view__comment-header">
                  <el-avatar :size="24">{{ comment.user.display_name?.charAt(0) }}</el-avatar>
                  <span class="task-detail-view__comment-user">{{ comment.user.display_name }}</span>
                  <span class="task-detail-view__comment-time">{{ formatDate(comment.created_at) }}</span>
                </div>
                <p class="task-detail-view__comment-body">{{ comment.content }}</p>
              </div>
            </div>
            <EmptyState v-else type="default" title="暂无评论" :padding="20" />

            <div class="task-detail-view__add-comment">
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
        </div>

        <div class="task-detail-view__sidebar">
          <div class="task-detail-view__section">
            <div class="task-detail-view__section-header">
              <h3>验收标准</h3>
            </div>
            <p v-if="task.acceptance_criteria" class="task-detail-view__sidebar-text">
              {{ task.acceptance_criteria }}
            </p>
            <EmptyState v-else type="default" title="暂无" :padding="12" />
          </div>

          <el-divider />

          <div class="task-detail-view__section">
            <div class="task-detail-view__section-header">
              <h3>Agent</h3>
            </div>
            <p v-if="task.agent_type">类型: {{ task.agent_type }}</p>
            <p v-else class="task-detail-view__na">未分配</p>
          </div>

          <el-divider />

          <div class="task-detail-view__section">
            <div class="task-detail-view__section-header">
              <h3>Hermes需求确认</h3>
            </div>
            <div class="task-detail-view__chat-box">
              <div class="task-detail-view__chat-messages" ref="chatMessagesRef">
                <div
                  v-for="(msg, idx) in chatMessages"
                  :key="idx"
                  :class="['task-detail-view__chat-msg', msg.role]"
                >
                  <div class="task-detail-view__chat-bubble">{{ msg.content }}</div>
                </div>
                <div v-if="chatLoading" class="task-detail-view__chat-msg hermes">
                  <div class="task-detail-view__chat-bubble hermes-thinking">思考中...</div>
                </div>
              </div>
              <div class="task-detail-view__chat-input-row">
                <el-input
                  v-model="chatInput"
                  placeholder="向Hermes描述需求..."
                  size="small"
                  :disabled="chatLoading"
                  @keyup.enter="handleChatSend"
                />
                <el-button type="primary" size="small" :loading="chatLoading" :disabled="!chatInput.trim()" @click="handleChatSend">
                  发送
                </el-button>
              </div>
              <div v-if="chatQuestions.length > 0" class="task-detail-view__chat-questions">
                <el-tag v-for="q in chatQuestions" :key="q" size="small" class="clickable" @click="chatInput = q; handleChatSend()">
                  {{ q }}
                </el-tag>
              </div>
            </div>
          </div>

          <el-divider />

          <div class="task-detail-view__section">
            <div class="task-detail-view__section-header">
              <h3>依赖关系</h3>
            </div>
            <TaskDependencyList
              :task-id="task.id"
              :predecessors="task.predecessors"
              :successors="task.successors"
            />
          </div>

          <el-divider />

          <div class="task-detail-view__section">
            <div class="task-detail-view__section-header">
              <h3>操作</h3>
            </div>
            <div class="task-detail-view__actions">
              <el-button :icon="Edit" @click="handleEdit">编辑任务</el-button>
              <el-button :icon="Aim" :loading="autoAssigning" @click="handleAgentAssign">Agent分配</el-button>
              <el-button :icon="Delete" type="danger" @click="handleDelete">删除任务</el-button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else-if="!loading" class="task-detail-view__not-found">
      <EmptyState type="default" title="任务不存在" description="找不到指定的任务">
        <el-button type="primary" @click="goBack" style="margin-top: 16px">返回看板</el-button>
      </EmptyState>
    </div>

    <TaskForm
      ref="taskFormRef"
      :board-id="boardId"
      :task-id="taskId"
      @success="handleTaskUpdated"
    />

    <ConfirmDialog
      ref="confirmDialogRef"
      title="删除任务"
      message="确定删除此任务吗？此操作不可撤销。"
      type="warning"
      @confirm="handleDeleteConfirm"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Edit, Delete, Aim } from '@element-plus/icons-vue'
import { useTaskStore } from '@/stores/useTaskStore'
import { workloadApi, apiClient } from '@/api'
import { format } from 'date-fns'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import PriorityBadge from '@/components/ui/PriorityBadge.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import TaskDependencyList from '@/components/tasks/TaskDependencyList.vue'
import TaskForm from '@/components/tasks/TaskForm.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

interface ChatMessage {
  role: 'hermes' | 'user'
  content: string
}

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()

const taskId = computed(() => route.params.taskId as string)
const boardId = computed(() => route.params.boardId as string)
const task = computed(() => taskStore.currentTask)
const loading = computed(() => taskStore.loading)

const newComment = ref('')
const commentLoading = ref(false)
const autoAssigning = ref(false)
const taskFormRef = ref()
const confirmDialogRef = ref()

const chatMessages = ref<ChatMessage[]>([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatQuestions = ref<string[]>([])
const chatMessagesRef = ref<HTMLElement | null>(null)

function scrollChat() {
  nextTick(() => {
    if (chatMessagesRef.value) {
      chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
    }
  })
}

async function handleChatSend() {
  const text = chatInput.value.trim()
  if (!text || chatLoading.value) return
  chatMessages.value.push({ role: 'user', content: text })
  chatInput.value = ''
  chatLoading.value = true
  chatQuestions.value = []
  scrollChat()
  try {
    const res = await apiClient.post('/projects/chat', {
      message: text,
      task_id: taskId.value,
    })
    const data = res.data?.data
    if (data) {
      chatMessages.value.push({ role: 'hermes', content: data.reply })
      chatQuestions.value = data.questions || []
    }
  } catch {
    chatMessages.value.push({ role: 'hermes', content: '抱歉，Hermes暂时无法回应，请稍后再试。' })
  } finally {
    chatLoading.value = false
    scrollChat()
  }
}

onMounted(async () => {
  if (taskId.value) {
    try {
      await taskStore.fetchDetail(taskId.value)
    } catch {
      ElMessage.error('获取任务详情失败')
    }
  }
})

function goBack() {
  router.push({ name: 'BoardDetail', params: { boardId: boardId.value } })
}

async function handleAgentAssign() {
  autoAssigning.value = true
  try {
    const res = await workloadApi.autoAssign(taskId.value)
    if (res.data?.assigned_to) {
      ElMessage.success(`Agent已将任务分配给 ${res.data.assigned_to.display_name}`)
      taskStore.fetchDetail(taskId.value)
    }
  } catch (e: any) {
    ElMessage.error(e.message || 'Agent分配失败')
  } finally {
    autoAssigning.value = false
  }
}

function handleEdit() {
  taskFormRef.value?.openForEdit(taskId.value)
}

function handleDelete() {
  confirmDialogRef.value?.open()
}

async function handleDeleteConfirm() {
  try {
    await taskStore.deleteTask(taskId.value)
    ElMessage.success('任务已删除')
    goBack()
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

async function handleAddComment() {
  if (!newComment.value.trim()) return
  commentLoading.value = true
  try {
    await taskStore.addComment(taskId.value, newComment.value.trim())
    newComment.value = ''
    ElMessage.success('评论已添加')
  } catch (e: any) {
    ElMessage.error(e.message || '添加评论失败')
  } finally {
    commentLoading.value = false
  }
}

function handleTaskUpdated() {
  taskStore.fetchDetail(taskId.value)
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
.task-detail-view {
  &__header {
    margin-bottom: $spacing-4;
  }

  &__main {
    display: flex;
    gap: $spacing-6;
  }

  &__content {
    flex: 1;
    min-width: 0;
  }

  &__sidebar {
    width: 320px;
    flex-shrink: 0;
  }

  &__title-section {
    margin-bottom: $spacing-4;
  }

  &__title {
    margin: 0 0 12px;
    font-size: $font-size-2xl;
    font-weight: $font-weight-bold;
    color: $text-color-primary;
  }

  &__status-bar {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  &__info {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  &__info-item {
    display: flex;
    flex-direction: column;
    gap: 2px;

    label {
      font-size: $font-size-xs;
      color: $text-color-placeholder;
    }

    .is-overdue {
      color: $status-blocked;
    }
  }

  &__na {
    color: $text-color-placeholder;
    font-style: italic;
  }

  &__tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  &__section {
    h3 {
      margin: 0 0 12px;
      font-size: $font-size-lg;
      color: $text-color-primary;
    }
  }

  &__section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  &__description {
    font-size: $font-size-base;
    color: $text-color-primary;
    line-height: 1.6;
    white-space: pre-wrap;
  }

  &__comment {
    margin-bottom: 12px;
    padding: 12px;
    background: $bg-color-body;
    border-radius: $radius-md;
  }

  &__comment-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }

  &__comment-user {
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: $text-color-primary;
  }

  &__comment-time {
    font-size: $font-size-xs;
    color: $text-color-placeholder;
    margin-left: auto;
  }

  &__comment-body {
    margin: 0;
    font-size: $font-size-sm;
    color: $text-color-primary;
    white-space: pre-wrap;
  }

  &__add-comment {
    margin-top: 16px;
  }

  &__actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  &__chat-box {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  &__chat-messages {
    max-height: 240px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 4px;
  }

  &__chat-msg {
    display: flex;
    &.user { justify-content: flex-end; }
    &.hermes { justify-content: flex-start; }
  }

  &__chat-bubble {
    max-width: 85%;
    padding: 6px 10px;
    border-radius: 8px;
    font-size: $font-size-sm;
    line-height: 1.4;
    word-break: break-word;
    white-space: pre-wrap;
    .user & {
      background: $primary-color;
      color: #fff;
    }
    .hermes & {
      background: $bg-color-body;
      color: $text-color-primary;
    }
    &.hermes-thinking {
      font-style: italic;
      color: $text-color-placeholder;
    }
  }

  &__sidebar-text {
    font-size: $font-size-sm;
    color: $text-color-primary;
    white-space: pre-wrap;
    line-height: 1.5;
  }

  &__chat-input-row {
    display: flex;
    gap: 6px;
  }

  &__chat-questions {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    .clickable {
      cursor: pointer;
    }
  }

  &__not-found {
    display: flex;
    justify-content: center;
    padding: 60px 0;
  }
}
</style>
