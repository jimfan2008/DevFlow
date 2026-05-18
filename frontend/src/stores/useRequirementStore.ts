import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { requirementApi } from '@/api'
import { projectSrsApi } from '@/api'
import { apiClient } from '@/api/client'
import { ElMessage } from 'element-plus'

export interface ChatMessage {
  role: 'hermes' | 'user'
  content: string
}

export interface ProjectItem {
  id: string
  name: string
  slug: string
  description?: string
}

export interface RequirementDoc {
  id?: string
  content: string
  version: number
  is_locked: boolean
  confirmed_at?: string
  created_at?: string
  updated_at?: string
}

export interface HermesStatus {
  connected: boolean
  mode: string
  version: string
  capabilities: string[]
  agent: Record<string, unknown> | null
}

export type ChatPhase = 'initial' | 'discussing' | 'summarizing'

export const useRequirementStore = defineStore('requirement', () => {
  const projects = ref<ProjectItem[]>([])
  const currentProjectId = ref<string | null>(null)
  const requirement = ref<RequirementDoc | null>(null)
  const hermesStatus = ref<HermesStatus | null>(null)
  const chatMessages = ref<ChatMessage[]>([])
  const chatLoading = ref(false)
  const chatPhase = ref<ChatPhase>('initial')
  const loading = ref(false)
  const submitting = ref(false)
  const error = ref<string | null>(null)
  const draftContent = ref('')

  const currentProject = computed(() =>
    projects.value.find(p => p.id === currentProjectId.value) || null,
  )

  const hasRequirement = computed(() => !!requirement.value?.content)
  const isConfirmed = computed(() => requirement.value?.is_locked ?? false)

  async function fetchProjects() {
    loading.value = true
    error.value = null
    try {
      const res = await apiClient.get('/projects') as any
      if (res?.data?.projects) {
        projects.value = res.data.projects
      }
    } catch (e: any) {
      error.value = e.message || '获取项目列表失败'
    } finally {
      loading.value = false
    }
  }

  async function createProject(name: string, description?: string) {
    loading.value = true
    error.value = null
    try {
      const res = await projectSrsApi.create({ name, description }) as any
      if (res?.data?.project) {
        const newProject: ProjectItem = {
          id: res.data.project.id,
          name: res.data.project.name,
          slug: res.data.project.slug,
          description,
        }
        projects.value.push(newProject)
        return newProject
      }
    } catch (e: any) {
      error.value = e.message || '创建项目失败'
    } finally {
      loading.value = false
    }
    return null
  }

  async function fetchRequirement(projectId: string) {
    if (!projectId) return
    loading.value = true
    error.value = null
    try {
      const res = await requirementApi.get(projectId) as any
      if (res?.data?.requirement) {
        requirement.value = res.data.requirement as RequirementDoc
        draftContent.value = requirement.value.content
      } else {
        requirement.value = null
        draftContent.value = ''
      }
    } catch (e: any) {
      error.value = e.message || '获取需求失败'
    } finally {
      loading.value = false
    }
  }

  async function submitRequirement(content: string) {
    if (!currentProjectId.value) return false
    submitting.value = true
    error.value = null
    try {
      const res = await requirementApi.submit(currentProjectId.value, { content }) as any
      if (res?.data?.requirement) {
        requirement.value = res.data.requirement as RequirementDoc
      }
      return true
    } catch (e: any) {
      error.value = e.message || '提交需求失败'
      return false
    } finally {
      submitting.value = false
    }
  }

  async function confirmRequirement() {
    if (!currentProjectId.value) return false
    loading.value = true
    error.value = null
    try {
      const res = await requirementApi.confirm(currentProjectId.value) as any
      if (res?.data?.requirement) {
        requirement.value = res.data.requirement as RequirementDoc
      }
      return true
    } catch (e: any) {
      error.value = e.message || '确认需求失败'
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchHermesStatus() {
    try {
      const res = await apiClient.get('/hermes/status') as any
      if (res?.data) {
        hermesStatus.value = res.data as HermesStatus
      }
    } catch {
      hermesStatus.value = {
        connected: false,
        mode: 'offline',
        version: '0.0.0',
        capabilities: [],
        agent: null,
      }
    }
  }

  async function sendChatMessage(message: string) {
    chatMessages.value.push({ role: 'user', content: message })
    chatLoading.value = true
    try {
      const res = await apiClient.post('/projects/chat', {
        message,
        project_id: currentProjectId.value,
      }) as any

      const data = res?.data
      if (data) {
        chatMessages.value.push({ role: 'hermes', content: data.reply })
        chatPhase.value = data.phase || 'discussing'
        return data
      }
    } catch {
      chatMessages.value.push({ role: 'hermes', content: '抱歉，与 Hermes 通信失败，请稍后重试。' })
    } finally {
      chatLoading.value = false
    }
    return null
  }

  async function sendIntro() {
    chatLoading.value = true
    try {
      const res = await apiClient.post('/projects/chat', {
        message: '介绍',
        project_id: currentProjectId.value,
      }) as any

      const data = res?.data
      if (data) {
        chatMessages.value.push({ role: 'hermes', content: data.reply })
        chatPhase.value = 'initial'
        return data
      }
    } catch {
      chatMessages.value.push({ role: 'hermes', content: '抱歉，与 Hermes 通信失败。' })
    } finally {
      chatLoading.value = false
    }
    return null
  }

  function selectProject(projectId: string) {
    currentProjectId.value = projectId
    requirement.value = null
    draftContent.value = ''
    chatMessages.value = []
    if (projectId) {
      fetchRequirement(projectId)
    }
  }

  return {
    projects,
    currentProjectId,
    requirement,
    hermesStatus,
    chatMessages,
    chatLoading,
    chatPhase,
    loading,
    submitting,
    error,
    draftContent,
    currentProject,
    hasRequirement,
    isConfirmed,
    fetchProjects,
    createProject,
    fetchRequirement,
    submitRequirement,
    confirmRequirement,
    fetchHermesStatus,
    sendChatMessage,
    sendIntro,
    selectProject,
  }
})
