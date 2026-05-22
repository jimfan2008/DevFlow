import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Repo, Branch, PullRequest, Commit } from '@/types/api'
import { repoApi } from '@/api'

export const useRepoStore = defineStore('repo', () => {
  const repos = ref<Repo[]>([])
  const currentRepo = ref<Repo | null>(null)
  const branches = ref<Branch[]>([])
  const pullRequests = ref<PullRequest[]>([])
  const commits = ref<Commit[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchRepos(projectId?: string) {
    loading.value = true
    error.value = null
    try {
      const res = await repoApi.list({ project_id: projectId }) as any
      if (res?.data?.repos) {
        repos.value = res.data.repos
      }
    } catch (e: any) {
      error.value = e.message || '获取仓库列表失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchRepoDetail(repoId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await repoApi.detail(repoId) as any
      if (res?.data?.repo) {
        currentRepo.value = res.data.repo
      }
    } catch (e: any) {
      error.value = e.message || '获取仓库详情失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchBranches(repoId: string) {
    try {
      const res = await repoApi.branches(repoId) as any
      if (res?.data?.branches) {
        branches.value = res.data.branches
      }
    } catch (e: any) {
      error.value = e.message || '获取分支失败'
    }
  }

  async function createBranch(repoId: string, name: string, base: string) {
    loading.value = true
    try {
      await repoApi.createBranch(repoId, { name, base })
      await fetchBranches(repoId)
    } catch (e: any) {
      error.value = e.message || '创建分支失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchPullRequests(repoId: string, state?: string) {
    try {
      const res = await repoApi.pullRequests(repoId, { state }) as any
      if (res?.data?.pulls) {
        pullRequests.value = res.data.pulls
      }
    } catch (e: any) {
      error.value = e.message || '获取PR列表失败'
    }
  }

  async function fetchCommits(repoId: string, branch?: string) {
    try {
      const res = await repoApi.commits(repoId, { branch }) as any
      if (res?.data?.commits) {
        commits.value = res.data.commits
      }
    } catch (e: any) {
      error.value = e.message || '获取提交记录失败'
    }
  }

  async function validateCommit(repoId: string, message: string) {
    try {
      const res = await repoApi.validateCommit(repoId, { message }) as any
      return res?.data || { valid: true, errors: [] }
    } catch {
      return { valid: true, errors: [] }
    }
  }

  return {
    repos,
    currentRepo,
    branches,
    pullRequests,
    commits,
    loading,
    error,
    fetchRepos,
    fetchRepoDetail,
    fetchBranches,
    createBranch,
    fetchPullRequests,
    fetchCommits,
    validateCommit,
  }
})
