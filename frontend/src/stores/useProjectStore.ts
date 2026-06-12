import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { Project, ProjectCreateRequest, ProjectCreateResult } from '@/types/api'
import { projectSrsApi } from '@/api'
import { apiClient } from '@/api/client'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const createResult = ref<ProjectCreateResult | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentPage = ref(1)
  const totalPages = ref(1)
  const totalItems = ref(0)
  const filterStatus = ref<string>('all')

  const filteredProjects = computed(() => {
    if (filterStatus.value === 'all') return projects.value
    return projects.value.filter(p => p.status === filterStatus.value)
  })

  async function fetchProjects(page = 1, pageSize = 12) {
    loading.value = true
    error.value = null
    try {
      const res = await apiClient.get('/projects', { params: { page, page_size: pageSize } }) as any
      const d = res?.data
      if (d?.projects) {
        projects.value = d.projects
        totalItems.value = d.total || d.projects.length
        totalPages.value = Math.ceil(totalItems.value / pageSize)
      }
    } catch (e: any) {
      error.value = e.message || '获取项目列表失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchProjectDetail(projectId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await apiClient.get(`/projects/${projectId}`) as any
      if (res?.data?.project) {
        currentProject.value = res.data.project
      }
    } catch (e: any) {
      error.value = e.message || '获取项目详情失败'
    } finally {
      loading.value = false
    }
  }

  async function createProject(data: ProjectCreateRequest) {
    loading.value = true
    error.value = null
    try {
      const res = await projectSrsApi.create(data) as any
      const proj = res?.data?.project ?? res?.project
      if (proj) {
        createResult.value = proj as ProjectCreateResult
        await fetchProjects(currentPage.value)
        return createResult.value
      }
    } catch (e: any) {
      error.value = e.message || '创建项目失败'
      ElMessage.error(e.message || '创建项目失败')
    } finally {
      loading.value = false
    }
    return null
  }

  async function fetchProjectTasks(projectId: string) {
    try {
      const res = await projectSrsApi.tasks(projectId) as any
      return res?.data?.tasks || []
    } catch {
      return []
    }
  }

  async function fetchProjectNotifications(projectId: string) {
    try {
      const res = await projectSrsApi.notifications(projectId) as any
      return res?.data || { notifications: [], total: 0, unread_count: 0 }
    } catch {
      return { notifications: [], total: 0, unread_count: 0 }
    }
  }

  async function completeProject(projectId: string) {
    loading.value = true
    try {
      const res = await projectSrsApi.complete(projectId) as any
      await fetchProjects(currentPage.value)
      return res?.data
    } catch (e: any) {
      error.value = e.message || '完成项目失败'
      return null
    } finally {
      loading.value = false
    }
  }

  async function deleteProject(projectId: string) {
    try {
      await apiClient.delete(`/projects/${projectId}`)
      projects.value = projects.value.filter(p => p.id !== projectId)
      return true
    } catch (e: any) {
      error.value = e.message || '删除项目失败'
      return false
    }
  }

  return {
    projects,
    currentProject,
    createResult,
    loading,
    error,
    currentPage,
    totalPages,
    totalItems,
    filterStatus,
    filteredProjects,
    fetchProjects,
    fetchProjectDetail,
    createProject,
    deleteProject,
    fetchProjectTasks,
    fetchProjectNotifications,
    completeProject,
  }
})
