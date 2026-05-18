/**
 * 任务状态管理
 * 管理任务列表、详情、创建/编辑/删除、看板拖拽批量移动
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  TaskBasic,
  TaskFull,
  TaskCreateRequest,
  TaskUpdateRequest,
  TaskBulkMoveRequest,
  TaskSearchRequest,
  TaskStatusValue,
  TaskPriorityValue,
} from '@/types/api'
import { taskApi, commentApi, attachmentApi } from '@/api'

export const useTaskStore = defineStore('task', () => {
  // ==================== 状态 ====================
  const taskList = ref<TaskBasic[]>([])
  const taskMap = ref<Record<string, TaskBasic>>({})
  const currentTask = ref<TaskFull | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentPage = ref(1)
  const totalPages = ref(1)
  const totalItems = ref(0)

  // ==================== 计算属性 ====================
  const hasData = computed(() => taskList.value.length > 0)
  const taskCount = computed(() => taskList.value.length)

  // ==================== 方法 ====================

  /**
   * 获取看板下的所有任务
   */
  async function fetchByBoard(boardId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await taskApi.byBoard(boardId, { page_size: 500 })
      if (res.data) {
        const d = res.data as any
        const tasks: TaskBasic[] = d.tasks || d.data || d
        taskList.value = tasks
        // 构建任务映射表
        const map: Record<string, TaskBasic> = {}
        tasks.forEach(task => { map[task.id] = task })
        taskMap.value = map
      }
      return res
    } catch (e: any) {
      error.value = e.message || '获取任务列表失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取分页任务列表
   */
  async function fetchList(params: Record<string, any> = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await taskApi.list(params)
      if (res.data) {
        taskList.value = res.data
        currentPage.value = res.meta?.page || 1
        totalPages.value = res.meta?.total_pages || 1
        totalItems.value = res.meta?.total || 0
      }
      return res
    } catch (e: any) {
      error.value = e.message || '获取任务列表失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取任务详情
   */
  async function fetchDetail(taskId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await taskApi.detail(taskId)
      if (res.data) {
        currentTask.value = res.data
      }
      return res
    } catch (e: any) {
      error.value = e.message || '获取任务详情失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建任务
   */
  async function createTask(data: TaskCreateRequest) {
    loading.value = true
    error.value = null
    try {
      const res = await taskApi.create(data)
      if (res.data) {
        // 刷新看板任务列表
        if (data.board_id) {
          await fetchByBoard(data.board_id)
        }
      }
      return res
    } catch (e: any) {
      error.value = e.message || '创建任务失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新任务
   */
  async function updateTask(taskId: string, data: TaskUpdateRequest) {
    loading.value = true
    error.value = null
    try {
      const res = await taskApi.update(taskId, data)
      if (res.data) {
        currentTask.value = res.data
        // 更新任务列表中的任务
        if (taskMap.value[taskId]) {
          taskMap.value[taskId] = { ...res.data }
        }
        const idx = taskList.value.findIndex(t => t.id === taskId)
        if (idx !== -1) {
          taskList.value[idx] = res.data
        }
      }
      return res
    } catch (e: any) {
      error.value = e.message || '更新任务失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 删除任务
   */
  async function deleteTask(taskId: string) {
    loading.value = true
    error.value = null
    try {
      await taskApi.delete(taskId)
      taskList.value = taskList.value.filter(t => t.id !== taskId)
      delete taskMap.value[taskId]
      if (currentTask.value?.id === taskId) {
        currentTask.value = null
      }
      return { code: 0, message: '删除成功' }
    } catch (e: any) {
      error.value = e.message || '删除任务失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 批量移动任务（看板拖拽后提交）
   * 使用 optimistic update 策略，先更新本地状态再请求 API
   */
  async function bulkMove(moves: TaskBulkMoveRequest['moves']) {
    loading.value = true
    error.value = null
    try {
      // 乐观更新：先更新本地状态
      const taskUpdates: Record<string, { column_id: string; position?: number }> = {}
      moves.forEach(move => {
        taskUpdates[move.task_id] = { column_id: move.column_id, position: move.position }
      })

      // 更新任务列表
      taskList.value = taskList.value.map(task => {
        const update = taskUpdates[task.id]
        if (update) {
          return { ...task, column_id: update.column_id, status: getColumnStatus(update.column_id, task) }
        }
        return task
      })

      // 更新任务映射
      moves.forEach(move => {
        if (taskMap.value[move.task_id]) {
          taskMap.value[move.task_id] = { ...taskMap.value[move.task_id], column_id: move.column_id }
        }
      })

      // 调用 API 持久化
      const res = await taskApi.bulkMove({ moves })
      return res
    } catch (e: any) {
      error.value = e.message || '移动任务失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 辅助：根据列推断状态（简化处理）
   */
  function getColumnStatus(columnId: string, task: TaskBasic): TaskStatusValue {
    // 实际应通过列名或配置映射，这里返回当前状态
    return task.status
  }

  /**
   * 搜索任务
   */
  async function search(params: TaskSearchRequest) {
    loading.value = true
    error.value = null
    try {
      const res = await taskApi.search(params)
      return res
    } catch (e: any) {
      error.value = e.message || '搜索任务失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 添加评论
   */
  async function addComment(taskId: string, content: string) {
    loading.value = true
    try {
      const res = await commentApi.create(taskId, { content })
      if (res.data && currentTask.value) {
        currentTask.value.comments.push(res.data)
      }
      return res
    } catch (e: any) {
      error.value = e.message || '添加评论失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 上传附件
   */
  async function uploadAttachment(taskId: string, file: File) {
    loading.value = true
    error.value = null
    try {
      const res = await attachmentApi.upload(taskId, file)
      if (res.data && currentTask.value) {
        currentTask.value.attachments.push(res.data)
      }
      return res
    } catch (e: any) {
      error.value = e.message || '上传附件失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 按状态分组任务（看板视图用）
   */
  function groupByColumn(tasks: TaskBasic[]): Record<string, TaskBasic[]> {
    const groups: Record<string, TaskBasic[]> = {}
    tasks.forEach(task => {
      if (!groups[task.column_id]) {
        groups[task.column_id] = []
      }
      groups[task.column_id].push(task)
    })
    return groups
  }

  /**
   * 按优先级过滤
   */
  function filterByPriority(tasks: TaskBasic[], priority: TaskPriorityValue | null) {
    if (!priority) return tasks
    return tasks.filter(t => t.priority === priority)
  }

  /**
   * 按状态过滤
   */
  function filterByStatus(tasks: TaskBasic[], status: TaskStatusValue | null) {
    if (!status) return tasks
    return tasks.filter(t => t.status === status)
  }

  /**
   * 清空当前任务详情
   */
  function clearCurrentTask() {
    currentTask.value = null
  }

  return {
    // 状态
    taskList,
    taskMap,
    currentTask,
    loading,
    error,
    currentPage,
    totalPages,
    totalItems,
    // 计算属性
    hasData,
    taskCount,
    // 方法
    fetchByBoard,
    fetchList,
    fetchDetail,
    createTask,
    updateTask,
    deleteTask,
    bulkMove,
    search,
    addComment,
    uploadAttachment,
    groupByColumn,
    filterByPriority,
    filterByStatus,
    clearCurrentTask,
  }
})
