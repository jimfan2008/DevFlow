<template>
  <el-card
    class="board-card"
    :body-style="{ padding: '16px' }"
    shadow="never"
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
  border-radius: $radius-lg;

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  &__title {
    margin: 0;
    font-family: $font-text;
    font-size: $body-strong-size;
    font-weight: $body-strong-weight;
    letter-spacing: $body-strong-tracking;
    color: $ink;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__delete {
    color: $ink-muted-48;
    cursor: pointer;
    flex-shrink: 0;
    &:hover { color: $priority-urgent; }
  }

  &__description {
    margin: 8px 0 0;
    font-size: $caption-size;
    color: $ink-muted-48;
    line-height: $caption-leading;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__meta {
    display: flex;
    gap: $spacing-4;
    margin-top: $spacing-sm;
    padding-top: $spacing-sm;
    border-top: 1px solid $hairline;
  }

  &__stat {
    display: flex;
    align-items: center;
    gap: $spacing-xxs;
    font-size: $fine-print-size;
    color: $ink-muted-48;
  }
}
</style>
