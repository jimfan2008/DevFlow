/**
 * 看板状态管理
 * 管理看板列表、详情、列、创建/编辑操作
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  BoardListItem,
  BoardDetail,
  BoardColumn,
  BoardCreateRequest,
  BoardUpdateRequest,
  ColumnCreateRequest,
  ColumnUpdateRequest,
  ColumnReorderRequest,
} from '@/types/api'
import { boardApi } from '@/api'

export const useBoardStore = defineStore('board', () => {
  // ==================== 状态 ====================
  const boardList = ref<BoardListItem[]>([])
  const currentBoard = ref<BoardDetail | null>(null)
  const columns = ref<BoardColumn[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentPage = ref(1)
  const totalPages = ref(1)
  const totalItems = ref(0)

  // ==================== 计算属性 ====================
  const hasData = computed(() => boardList.value.length > 0)
  const columnMap = computed(() => {
    const map: Record<string, BoardColumn> = {}
    columns.value.forEach(col => { map[col.id] = col })
    return map
  })

  // ==================== 方法 ====================

  /**
   * 获取看板列表
   */
  async function fetchBoardList(page = 1, pageSize = 12) {
    loading.value = true
    error.value = null
    try {
      const res = await boardApi.list({ page, page_size: pageSize })
      if (res.data) {
        const d = res.data as any
        boardList.value = d.boards || d.data || d
        currentPage.value = res.meta?.page || d.page || 1
        totalPages.value = res.meta?.total_pages || d.total_pages || 1
        totalItems.value = res.meta?.total || d.total || 0
      }
      return res
    } catch (e: any) {
      error.value = e.message || '获取看板列表失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取看板详情（包含列信息）
   */
  async function fetchBoardDetail(boardId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await boardApi.detail(boardId)
      if (res.data) {
        const d = res.data as any
        const board = d.board || d
        currentBoard.value = board
        columns.value = board.columns || d.columns || []
      }
      return res
    } catch (e: any) {
      error.value = e.message || '获取看板详情失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建看板
   */
  async function createBoard(data: BoardCreateRequest) {
    loading.value = true
    error.value = null
    try {
      const res = await boardApi.create(data)
      // 刷新列表
      if (res.data) {
        await fetchBoardList(currentPage.value)
      }
      return res
    } catch (e: any) {
      error.value = e.message || '创建看板失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新看板信息
   */
  async function updateBoard(boardId: string, data: BoardUpdateRequest) {
    loading.value = true
    error.value = null
    try {
      const res = await boardApi.update(boardId, data)
      // 如果当前看板正在查看，更新详情
      if (res.data && currentBoard.value?.id === boardId) {
        currentBoard.value = res.data
      }
      // 刷新列表
      await fetchBoardList(currentPage.value)
      return res
    } catch (e: any) {
      error.value = e.message || '更新看板失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 删除看板
   */
  async function deleteBoard(boardId: string) {
    loading.value = true
    error.value = null
    try {
      await boardApi.delete(boardId)
      // 从列表中移除
      boardList.value = boardList.value.filter(b => b.id !== boardId)
      // 如果当前看板被删除，清空详情
      if (currentBoard.value?.id === boardId) {
        currentBoard.value = null
        columns.value = []
      }
      return { code: 0, message: '删除成功' }
    } catch (e: any) {
      error.value = e.message || '删除看板失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建列
   */
  async function createColumn(boardId: string, data: ColumnCreateRequest) {
    loading.value = true
    error.value = null
    try {
      const res = await boardApi.createColumn(boardId, data)
      // 刷新看板详情
      await fetchBoardDetail(boardId)
      return res
    } catch (e: any) {
      error.value = e.message || '创建列失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新列
   */
  async function updateColumn(boardId: string, columnId: string, data: ColumnUpdateRequest) {
    loading.value = true
    error.value = null
    try {
      const res = await boardApi.updateColumn(boardId, columnId, data)
      // 刷新看板详情
      await fetchBoardDetail(boardId)
      return res
    } catch (e: any) {
      error.value = e.message || '更新列失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 删除列
   */
  async function deleteColumn(boardId: string, columnId: string) {
    loading.value = true
    error.value = null
    try {
      await boardApi.deleteColumn(boardId, columnId)
      // 刷新看板详情
      await fetchBoardDetail(boardId)
      return { code: 0, message: '删除成功' }
    } catch (e: any) {
      error.value = e.message || '删除列失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 列重新排序
   */
  async function reorderColumns(boardId: string, columnsOrder: { column_id: string; position: number }[]) {
    loading.value = true
    error.value = null
    try {
      const res = await boardApi.reorderColumns(boardId, { columns: columnsOrder })
      if (res.data?.columns) {
        columns.value = res.data.columns
      }
      return res
    } catch (e: any) {
      error.value = e.message || '列重排序失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 清空当前看板详情
   */
  function clearCurrentBoard() {
    currentBoard.value = null
    columns.value = []
  }

  return {
    // 状态
    boardList,
    currentBoard,
    columns,
    loading,
    error,
    currentPage,
    totalPages,
    totalItems,
    // 计算属性
    hasData,
    columnMap,
    // 方法
    fetchBoardList,
    fetchBoardDetail,
    createBoard,
    updateBoard,
    deleteBoard,
    createColumn,
    updateColumn,
    deleteColumn,
    reorderColumns,
    clearCurrentBoard,
  }
})
