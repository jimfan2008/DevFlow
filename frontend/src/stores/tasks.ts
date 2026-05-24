import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MeetingOutcome, TaskItem } from '@/types'
import { apiClient } from '@/api'

export const useTasksStore = defineStore('tasks', () => {
  const meetingOutcomes = ref<Record<string, MeetingOutcome[]>>({})
  const tasks = ref<Record<string, TaskItem[]>>({})

  function getMeetingOutcomes(groupId: string): MeetingOutcome[] {
    return meetingOutcomes.value[groupId] || []
  }

  function addMeetingOutcome(groupId: string, outcome: MeetingOutcome) {
    if (!meetingOutcomes.value[groupId]) {
      meetingOutcomes.value[groupId] = []
    }
    meetingOutcomes.value[groupId].unshift(outcome)
  }

  function getTasks(groupId: string): TaskItem[] {
    return tasks.value[groupId] || []
  }

  function addTask(groupId: string, task: TaskItem) {
    if (!tasks.value[groupId]) {
      tasks.value[groupId] = []
    }
    const idx = tasks.value[groupId].findIndex(t => t.id === task.id)
    if (idx >= 0) {
      tasks.value[groupId][idx] = task
    } else {
      tasks.value[groupId].push(task)
    }
  }

  function updateTaskStatus(taskId: string, status: string) {
    for (const groupId in tasks.value) {
      const task = tasks.value[groupId].find(t => t.id === taskId)
      if (task) {
        task.status = status
        if (status === 'completed') {
          task.completed_at = new Date().toISOString()
        }
        break
      }
    }
  }

  async function fetchMeetingOutcomes(groupId: string) {
    try {
      const response = await apiClient.get(`/groups/${groupId}/outcomes`)
      const data = (response as any)?.data || (response as any)?.outcomes || (response as any)?.data?.outcomes
      if (Array.isArray(data)) {
        meetingOutcomes.value[groupId] = data
      }
    } catch (e) {
      console.error('Error fetching meeting outcomes:', e)
    }
  }

  async function fetchTasks(groupId: string) {
    try {
      const response = await apiClient.get(`/groups/${groupId}/tasks`)
      const data = (response as any)?.data || (response as any)?.tasks || (response as any)?.data?.tasks
      if (Array.isArray(data)) {
        tasks.value[groupId] = data
      }
    } catch (e) {
      console.error('Error fetching tasks:', e)
    }
  }

  return {
    meetingOutcomes,
    tasks,
    getMeetingOutcomes,
    addMeetingOutcome,
    getTasks,
    addTask,
    updateTaskStatus,
    fetchMeetingOutcomes,
    fetchTasks,
  }
})