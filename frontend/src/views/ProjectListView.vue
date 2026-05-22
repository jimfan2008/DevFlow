<template>
  <div class="project-list-view">
    <div class="project-list-view__header">
      <h2 class="project-list-view__title">项目管理</h2>
      <div class="project-list-view__actions">
        <el-select v-model="store.filterStatus" placeholder="状态筛选" style="width: 140px" clearable @change="handleFilterChange">
          <el-option label="全部" value="all" />
          <el-option label="草稿" value="draft" />
          <el-option label="进行中" value="active" />
          <el-option label="已完成" value="completed" />
          <el-option label="已归档" value="archived" />
        </el-select>
        <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">创建项目</el-button>
      </div>
    </div>

    <div v-loading="store.loading" class="project-list-view__grid">
      <el-card
        v-for="project in store.filteredProjects"
        :key="project.id"
        class="project-list-view__card"
        shadow="hover"
        @click="goToDetail(project.id)"
      >
        <template #header>
          <div class="project-list-view__card-header">
            <span class="project-list-view__card-name">{{ project.name }}</span>
            <div style="display:flex;align-items:center;gap:8px">
              <el-tag :type="statusTagType(project.status)" size="small">{{ statusLabel(project.status) }}</el-tag>
              <el-button type="danger" size="small" :icon="Delete" circle @click.stop="handleDeleteProject(project)" />
            </div>
          </div>
        </template>
        <p class="project-list-view__card-desc">{{ project.description || '暂无描述' }}</p>
        <div class="project-list-view__card-meta">
          <span>{{ formatDate(project.created_at) }}</span>
        </div>
      </el-card>
    </div>

    <div v-if="!store.loading && store.projects.length === 0" class="project-list-view__empty">
      <el-empty description="暂无项目">
        <el-button type="primary" @click="showCreateDialog = true">创建项目</el-button>
      </el-empty>
    </div>

    <div v-if="store.totalPages > 1" class="project-list-view__pagination">
      <el-pagination
        v-model:current-page="store.currentPage"
        :total="store.totalItems"
        :page-size="12"
        layout="prev, pager, next"
        @current-change="handlePageChange"
      />
    </div>

    <el-dialog v-model="showCreateDialog" title="创建项目" width="480px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="项目名称" required>
          <el-input v-model="createForm.name" placeholder="输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="简要描述项目" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="store.loading" :disabled="!createForm.name.trim()" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useProjectStore } from '@/stores/useProjectStore'

const router = useRouter()
const store = useProjectStore()
const showCreateDialog = ref(false)
const createForm = ref({ name: '', description: '' })

onMounted(() => {
  store.fetchProjects(1, 12)
})

function handlePageChange(page: number) {
  store.fetchProjects(page, 12)
}

function handleFilterChange() {
  store.fetchProjects(1, 12)
}

function goToDetail(projectId: string) {
  router.push({ name: 'ProjectDetail', params: { projectId } })
}

async function handleCreate() {
  const project = await store.createProject({ name: createForm.value.name, description: createForm.value.description || undefined })
  if (project) {
    ElMessage.success('项目创建成功')
    showCreateDialog.value = false
    createForm.value = { name: '', description: '' }
  }
}

async function handleDeleteProject(project: any) {
  try {
    await ElMessageBox.confirm(`确定删除项目"${project.name}"？`, '删除确认', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
    const ok = await store.deleteProject(project.id)
    if (ok) ElMessage.success('已删除')
  } catch {}
}

function statusLabel(status: string) {
  const map: Record<string, string> = { draft: '草稿', active: '进行中', completed: '已完成', archived: '已归档' }
  return map[status] || status
}

function statusTagType(status: string) {
  const map: Record<string, string> = { draft: 'info', active: '', completed: 'success', archived: 'warning' }
  return (map[status] || 'info') as any
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('zh-CN')
}
</script>

<style lang="scss" scoped>
.project-list-view {
  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-6;
  }
  &__title {
    margin: 0;
    font-size: $font-size-2xl;
    font-weight: $font-weight-bold;
    color: $text-color-primary;
  }
  &__actions {
    display: flex;
    gap: $spacing-2;
  }
  &__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: $spacing-4;
  }
  &__card {
    cursor: pointer;
    &-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    &-name {
      font-weight: $font-weight-semibold;
      font-size: $font-size-md;
    }
    &-desc {
      color: $text-color-secondary;
      font-size: $font-size-sm;
      margin: 0 0 $spacing-2 0;
    }
    &-meta {
      font-size: $font-size-xs;
      color: $text-color-placeholder;
    }
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
