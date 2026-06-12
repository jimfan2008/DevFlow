<template>
  <div class="repo-view">
    <div class="repo-view__header">
      <h2 class="repo-view__title">代码仓库</h2>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="仓库列表" name="list">
        <div v-loading="store.loading" class="repo-view__grid">
          <el-card v-for="repo in store.repos" :key="repo.id" shadow="never" class="repo-view__card" @click="goToRepoDetail(repo.id)">
            <template #header>
              <div class="repo-view__card-header">
                <span class="repo-view__card-name">{{ repo.full_name || repo.name }}</span>
                <el-tag size="small">{{ repo.default_branch }}</el-tag>
              </div>
            </template>
            <div class="repo-view__card-body">
              <el-link :href="repo.url" target="_blank" type="primary" :underline="false">{{ repo.url }}</el-link>
            </div>
          </el-card>
        </div>
        <el-empty v-if="!store.loading && store.repos.length === 0" description="暂无仓库" />
      </el-tab-pane>

      <el-tab-pane v-if="currentRepoId" label="仓库详情" name="detail">
        <div v-if="store.currentRepo" class="repo-view__detail">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="仓库名称">{{ store.currentRepo.full_name }}</el-descriptions-item>
            <el-descriptions-item label="默认分支">{{ store.currentRepo.default_branch }}</el-descriptions-item>
            <el-descriptions-item label="URL" :span="2">
              <el-link :href="store.currentRepo.url" target="_blank" type="primary">{{ store.currentRepo.url }}</el-link>
            </el-descriptions-item>
          </el-descriptions>

          <h3 style="margin-top: 24px">分支列表</h3>
          <el-table :data="store.branches" stripe>
            <el-table-column prop="name" label="分支名" />
            <el-table-column prop="commit_sha" label="Commit" width="120">
              <template #default="{ row }">{{ row.commit_sha?.slice(0, 8) }}</template>
            </el-table-column>
            <el-table-column label="默认" width="60">
              <template #default="{ row }"><el-tag v-if="row.is_default" type="success" size="small">是</el-tag></template>
            </el-table-column>
            <el-table-column label="受保护" width="80">
              <template #default="{ row }"><el-tag v-if="row.is_protected" type="warning" size="small">是</el-tag></template>
            </el-table-column>
          </el-table>

          <h3 style="margin-top: 24px">Pull Requests</h3>
          <el-table :data="store.pullRequests" stripe>
            <el-table-column label="#" width="60">
              <template #default="{ row }">{{ row.number }}</template>
            </el-table-column>
            <el-table-column prop="title" label="标题" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.state === 'merged' ? 'success' : row.state === 'open' ? '' : 'info'" size="small">{{ row.state }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="source_branch" label="源分支" width="120" />
            <el-table-column prop="target_branch" label="目标分支" width="120" />
          </el-table>

          <h3 style="margin-top: 24px">提交记录</h3>
          <el-table :data="store.commits" stripe>
            <el-table-column label="SHA" width="80">
              <template #default="{ row }">{{ row.sha?.slice(0, 8) }}</template>
            </el-table-column>
            <el-table-column prop="message" label="消息" />
            <el-table-column prop="author_name" label="作者" width="100" />
            <el-table-column label="规范" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_conventional ? 'success' : 'danger'" size="small">{{ row.is_conventional ? '通过' : '不合规' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="branchDialogVisible" title="创建分支" width="400px">
      <el-form :model="branchForm" label-width="80px">
        <el-form-item label="分支名" required>
          <el-input v-model="branchForm.name" placeholder="feature/xxx" />
        </el-form-item>
        <el-form-item label="基于分支">
          <el-input v-model="branchForm.base" placeholder="main" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="branchDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="store.loading" @click="handleCreateBranch">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRepoStore } from '@/stores/useRepoStore'

const store = useRepoStore()
const activeTab = ref('list')
const currentRepoId = ref('')
const branchDialogVisible = ref(false)
const branchForm = ref({ name: '', base: 'main' })

onMounted(() => {
  store.fetchRepos()
})

async function goToRepoDetail(repoId: string) {
  currentRepoId.value = repoId
  activeTab.value = 'detail'
  await Promise.all([
    store.fetchRepoDetail(repoId),
    store.fetchBranches(repoId),
    store.fetchPullRequests(repoId),
    store.fetchCommits(repoId),
  ])
}

async function handleCreateBranch() {
  if (!currentRepoId.value || !branchForm.value.name) return
  await store.createBranch(currentRepoId.value, branchForm.value.name, branchForm.value.base)
  branchDialogVisible.value = false
  ElMessage.success('分支创建成功')
  branchForm.value = { name: '', base: 'main' }
}
</script>

<style lang="scss" scoped>
.repo-view {
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
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: $spacing-lg;
  }
  &__card {
    cursor: pointer;
    border-radius: $radius-lg;
    &-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    &-name {
      font-family: $font-text;
      font-size: $body-strong-size;
      font-weight: $body-strong-weight;
      letter-spacing: $body-strong-tracking;
    }
    &-body {
      font-size: $caption-size;
    }
  }
  &__detail {
    h3 {
      font-family: $font-text;
      font-size: $body-strong-size;
      font-weight: $body-strong-weight;
      letter-spacing: $body-strong-tracking;
      color: $ink;
    }
  }
}
</style>
