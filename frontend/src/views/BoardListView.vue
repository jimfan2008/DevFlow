<template>
  <div class="board-list-view">
    <div class="board-list-view__header">
      <h2 class="board-list-view__title">看板列表</h2>
      <el-button type="primary" :icon="Plus" @click="createBoardDialogRef?.open()">
        创建看板
      </el-button>
    </div>

    <div v-loading="boardStore.loading" class="board-list-view__grid">
      <BoardCard
        v-for="board in boardStore.boardList"
        :key="board.id"
        :board="board"
        :can-delete="true"
      />
    </div>

    <div class="board-list-view__empty" v-if="!boardStore.loading && boardStore.boardList.length === 0">
      <EmptyState
        type="default"
        title="暂无看板"
        description="创建第一个看板开始管理项目"
      >
         <el-button type="primary" :icon="Plus" @click="createBoardDialogRef?.open()" style="margin-top: 16px">
          创建看板
         </el-button>
      </EmptyState>
    </div>

    <div v-if="boardStore.totalPages > 1" class="board-list-view__pagination">
      <el-pagination
        v-model:current-page="boardStore.currentPage"
        :page-size="12"
        :total="boardStore.totalItems"
        layout="prev, pager, next"
        @current-change="handlePageChange"
      />
    </div>

    <CreateBoardDialog
      ref="createBoardDialogRef"
      @success="handleBoardCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { useBoardStore } from '@/stores/useBoardStore'
import BoardCard from '@/components/common/BoardCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import CreateBoardDialog from '@/components/boards/CreateBoardDialog.vue'

const router = useRouter()
const boardStore = useBoardStore()
const createBoardDialogRef = ref()

onMounted(async () => {
  await boardStore.fetchBoardList(1, 12)
})

function handlePageChange(page: number) {
  boardStore.fetchBoardList(page, 12)
}

async function handleBoardCreated() {
  await boardStore.fetchBoardList(boardStore.currentPage, 12)
  if (boardStore.boardList.length > 0) {
    const newest = boardStore.boardList[0]
    router.push({ name: 'BoardDetail', params: { boardId: newest.id } })
  }
}
</script>

<style lang="scss" scoped>
.board-list-view {
  height: 100%;
  display: flex;
  flex-direction: column;

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-6;
  }

  &__title {
    margin: 0;
    font-family: $font-display;
    font-size: $display-lg-size;
    font-weight: $display-lg-weight;
    line-height: $display-lg-leading;
    letter-spacing: $display-lg-tracking;
    color: $ink;
  }
  &__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: $spacing-lg;
  }

  &__empty {
    display: flex;
    justify-content: center;
    padding: 60px 0;
  }

  &__pagination {
    display: flex;
    justify-content: center;
    padding: $spacing-6 0;
  }
}
</style>
