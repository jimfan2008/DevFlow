<template>
  <div class="board-detail-view">
    <KanbanBoard :board-id="boardId" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import KanbanBoard from '@/components/boards/KanbanBoard.vue'

const route = useRoute()
const boardId = computed(() => route.params.boardId as string)
</script>

<style lang="scss" scoped>
.board-detail-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>
