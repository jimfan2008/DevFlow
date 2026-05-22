import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Skill, SkillExecutionRecord } from '@/types/api'
import { skillApi } from '@/api'

export const useSkillStore = defineStore('skill', () => {
  const skills = ref<Skill[]>([])
  const executionHistory = ref<SkillExecutionRecord[]>([])
  const currentSkill = ref<Skill | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentPage = ref(1)
  const totalItems = ref(0)

  async function fetchSkills(hermesAgentId?: string) {
    loading.value = true
    error.value = null
    try {
      const res = await skillApi.list({ hermes_agent_id: hermesAgentId }) as any
      if (res?.data?.skills) {
        skills.value = res.data.skills
        totalItems.value = res.data.total || skills.value.length
      }
    } catch (e: any) {
      error.value = e.message || '获取Skill列表失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchSkillDetail(skillId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await skillApi.detail(skillId) as any
      if (res?.data?.skill) {
        currentSkill.value = res.data.skill
      }
    } catch (e: any) {
      error.value = e.message || '获取Skill详情失败'
    } finally {
      loading.value = false
    }
  }

  async function discoverAgents(skillId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await skillApi.discoverAgents(skillId) as any
      await fetchSkillDetail(skillId)
      return res?.data?.discovered || []
    } catch (e: any) {
      error.value = e.message || '发现编程Agent失败'
      return []
    } finally {
      loading.value = false
    }
  }

  async function pairAgent(skillId: string, agentId: string, channelConfig?: Record<string, unknown>) {
    loading.value = true
    error.value = null
    try {
      await skillApi.pairAgent(skillId, { agent_id: agentId, channel_config: channelConfig })
      await fetchSkillDetail(skillId)
    } catch (e: any) {
      error.value = e.message || '对接Agent失败'
    } finally {
      loading.value = false
    }
  }

  async function assignTask(skillId: string, taskId: string, subtaskConfig?: Record<string, unknown>) {
    loading.value = true
    error.value = null
    try {
      await skillApi.assignTask(skillId, { task_id: taskId, subtask_config: subtaskConfig })
      await fetchSkillDetail(skillId)
    } catch (e: any) {
      error.value = e.message || '分配任务失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchExecutionHistory(skillId?: string, page = 1) {
    loading.value = true
    try {
      const res = await skillApi.history({ skill_id: skillId, page, page_size: 20 }) as any
      if (res?.data?.records) {
        executionHistory.value = res.data.records
        totalItems.value = res.data.total || 0
      }
    } catch (e: any) {
      error.value = e.message || '获取执行历史失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchChannelStatus(skillId: string) {
    try {
      const res = await skillApi.channelStatus(skillId) as any
      return res?.data?.channel || null
    } catch {
      return null
    }
  }

  return {
    skills,
    executionHistory,
    currentSkill,
    loading,
    error,
    currentPage,
    totalItems,
    fetchSkills,
    fetchSkillDetail,
    discoverAgents,
    pairAgent,
    assignTask,
    fetchExecutionHistory,
    fetchChannelStatus,
  }
})
