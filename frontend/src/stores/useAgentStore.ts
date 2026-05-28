import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Agent } from '@/types/api'
import { agentApi } from '@/api'
import { apiClient } from '@/api/client'

export const useAgentStore = defineStore('agent', () => {
  const agents = ref<Agent[]>([])
  const currentAgent = ref<Agent | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchAgents(agentType?: string) {
    loading.value = true
    error.value = null
    try {
      const res = await agentApi.list(agentType) as any
      if (res?.data?.agents) {
        agents.value = res.data.agents
      }
    } catch (e: any) {
      error.value = e.message || '获取Agent列表失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchAgentDetail(agentId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await agentApi.detail(agentId) as any
      if (res?.data?.agent) {
        currentAgent.value = res.data.agent
      }
    } catch (e: any) {
      error.value = e.message || '获取Agent详情失败'
    } finally {
      loading.value = false
    }
  }

  async function updateAgentStatus(agentId: string, status: 'online' | 'offline' | 'busy') {
    try {
      await agentApi.updateStatus(agentId, status)
      const agent = agents.value.find(a => a.id === agentId)
      if (agent) agent.status = status
      if (currentAgent.value?.id === agentId) currentAgent.value.status = status
    } catch (e: any) {
      error.value = e.message || '更新状态失败'
    }
  }

  async function deleteAgent(agentId: string) {
    try {
      await agentApi.delete(agentId)
      agents.value = agents.value.filter(a => a.id !== agentId)
      if (currentAgent.value?.id === agentId) currentAgent.value = null
      return true
    } catch (e: any) {
      error.value = e.message || '删除Agent失败'
      return false
    }
  }

  async function triggerProfileScan() {
    try {
      const res = await apiClient.post('/agents/scan-profile') as any
      await fetchAgents()
      return res?.data
    } catch (e: any) {
      error.value = e.message || 'Profile扫描失败'
      return null
    }
  }

  async function triggerSkillDiscovery(agentId: string) {
    try {
      const res = await apiClient.post(`/agents/${agentId}/discover-skills`) as any
      await fetchAgentDetail(agentId)
      return res?.data
    } catch (e: any) {
      error.value = e.message || 'Skill发现失败'
      return null
    }
  }

  async function fetchAgentLoad(agentId: string) {
    try {
      const res = await agentApi.load(agentId) as any
      return res?.data?.load || null
    } catch {
      return null
    }
  }

  return {
    agents,
    currentAgent,
    loading,
    error,
    fetchAgents,
    fetchAgentDetail,
    updateAgentStatus,
    deleteAgent,
    triggerProfileScan,
    triggerSkillDiscovery,
    fetchAgentLoad,
  }
})
