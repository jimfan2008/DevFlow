<template>
  <div class="task-dependency">
    <div class="task-dependency__section">
      <div class="task-dependency__header">
        <h5>前置任务（{{ predecessors.length }}）</h5>
        <el-button v-if="!showAddPredecessor" text size="small" :icon="Plus" @click="showAddPredecessor = true">
          添加
        </el-button>
      </div>
      <div v-if="showAddPredecessor" class="task-dependency__add">
        <el-input
          v-model="predecessorSearch"
          placeholder="输入任务标题搜索..."
          size="small"
          clearable
        />
        <div v-if="searchResults.length > 0" class="task-dependency__search-results">
          <div
            v-for="result in searchResults.slice(0, 5)"
            :key="result.id"
            class="task-dependency__search-item"
            @click="addPredecessor(result.id)"
          >
            <span>{{ result.title }}</span>
            <StatusBadge :status="result.status" />
          </div>
        </div>
        <div class="task-dependency__actions">
          <el-button size="small" type="primary" :loading="addingDep" @click="addPredecessorById">
            确定
          </el-button>
          <el-button size="small" @click="showAddPredecessor = false">取消</el-button>
        </div>
      </div>
      <div v-if="predecessors.length === 0 && !showAddPredecessor" class="task-dependency__empty">
        无前置任务
      </div>
      <div v-for="dep in predecessors" :key="dep.id" class="task-dependency__item">
        <div class="task-dependency__item-info">
          <span class="task-dependency__item-title">{{ dep.title }}</span>
          <StatusBadge :status="dep.status" />
        </div>
        <el-button
          :icon="Delete"
          text
          size="small"
          @click="removeDependency(dep.id)"
        />
      </div>
    </div>

    <el-divider />

    <div class="task-dependency__section">
      <div class="task-dependency__header">
        <h5>后置任务（{{ successors.length }}）</h5>
      </div>
      <div v-if="successors.length === 0" class="task-dependency__empty">无后置任务</div>
      <div v-for="dep in successors" :key="dep.id" class="task-dependency__item">
        <div class="task-dependency__item-info">
          <span class="task-dependency__item-title">{{ dep.title }}</span>
          <StatusBadge :status="dep.status" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { dependencyApi } from '@/api'
import { useTaskStore } from '@/stores/useTaskStore'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import type { TaskBrief } from '@/types/api'

const props = defineProps<{
  taskId: string
  predecessors: TaskBrief[]
  successors: TaskBrief[]
}>()

const taskStore = useTaskStore()

const showAddPredecessor = ref(false)
const predecessorSearch = ref('')
const searchResults = ref<TaskBrief[]>([])
const addingDep = ref(false)

watch(predecessorSearch, async (val) => {
  if (!val.trim()) {
    searchResults.value = []
    return
  }
  try {
    const res = await taskStore.search({ q: val.trim(), limit: 5 })
    searchResults.value = res.data || []
  } catch {
    searchResults.value = []
  }
})

async function addPredecessor(taskId: string) {
  addingDep.value = true
  try {
    await dependencyApi.create(props.taskId, { predecessor_id: taskId })
    ElMessage.success('依赖已添加')
    showAddPredecessor.value = false
    predecessorSearch.value = ''
    taskStore.fetchDetail(props.taskId)
  } catch (e: any) {
    ElMessage.error(e.message || '添加依赖失败')
  } finally {
    addingDep.value = false
  }
}

function addPredecessorById() {
  // Stub: in a real app you'd select from search results
}

async function removeDependency(dependencyId: string) {
  try {
    await dependencyApi.delete(dependencyId)
    ElMessage.success('依赖已移除')
    taskStore.fetchDetail(props.taskId)
  } catch (e: any) {
    ElMessage.error(e.message || '移除依赖失败')
  }
}
</script>

<style lang="scss" scoped>
.task-dependency {
  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-xs;

    h5 {
      margin: 0;
      font-family: $font-text;
      font-size: $body-strong-size;
      font-weight: $body-strong-weight;
      letter-spacing: $body-strong-tracking;
      color: $ink;
    }
  }

  &__item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: $spacing-xxs $spacing-xs;
    background: $canvas-parchment;
    border-radius: $radius-sm;
    margin-bottom: $spacing-xxs;
  }

  &__item-info {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    overflow: hidden;
  }

  &__item-title {
    font-family: $font-text;
    font-size: $body-size;
    color: $ink;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__empty {
    font-family: $font-text;
    font-size: $body-size;
    color: $ink-muted-48;
    padding: $spacing-xs 0;
  }

  &__add { margin-bottom: $spacing-xs; }

  &__search-results {
    margin-top: $spacing-xxs;
    border: 1px solid $hairline;
    border-radius: $radius-sm;
    max-height: 200px;
    overflow-y: auto;
  }

  &__search-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: $spacing-xxs $spacing-xs;
    cursor: pointer;
    font-family: $font-text;
    font-size: $body-size;

    &:hover { background: $canvas-parchment; }
  }

  &__actions {
    display: flex;
    gap: $spacing-xs;
    margin-top: $spacing-xs;
  }
}
</style>
