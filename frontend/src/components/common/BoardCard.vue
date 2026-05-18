<template>
  <el-card
    class="board-card"
    :body-style="{ padding: '16px' }"
    shadow="hover"
    @click="handleClick"
  >
    <div class="board-card__header">
      <h3 class="board-card__title">{{ board.name }}</h3>
      <el-icon v-if="canDelete" class="board-card__delete" @click.stop="handleDelete">
        <Delete />
      </el-icon>
    </div>
    <p v-if="board.description" class="board-card__description">{{ board.description }}</p>
    <div class="board-card__meta">
      <span class="board-card__stat">
        <el-icon><Collection /></el-icon>
        {{ board.column_count }} 列
      </span>
      <span class="board-card__stat">
        <el-icon><Edit /></el-icon>
        {{ board.task_count }} 任务
      </span>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Delete, Collection, Edit } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useBoardStore } from '@/stores/useBoardStore'
import type { BoardListItem } from '@/types/api'

const props = defineProps<{
  board: BoardListItem
  canDelete?: boolean
}>()

const router = useRouter()
const boardStore = useBoardStore()

function handleClick() {
  router.push({ name: 'BoardDetail', params: { boardId: props.board.id } })
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm(`确定删除看板"${props.board.name}"？此操作不可撤销。`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await boardStore.deleteBoard(props.board.id)
    ElMessage.success('看板已删除')
  } catch {
    // 取消或失败不处理
  }
}
</script>

<style lang="scss" scoped>
.board-card {
  cursor: pointer;
  transition: transform 0.2s;

  &:hover {
    transform: translateY(-2px);
  }

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  &__title {
    margin: 0;
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    color: $text-color-primary;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__delete {
    color: $text-color-placeholder;
    cursor: pointer;
    flex-shrink: 0;

    &:hover {
      color: $priority-urgent;
    }
  }

  &__description {
    margin: 8px 0 0;
    font-size: $font-size-sm;
    color: $text-color-secondary;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__meta {
    display: flex;
    gap: 16px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid $border-color-light;
  }

  &__stat {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: $font-size-xs;
    color: $text-color-placeholder;
  }
}
</style>
