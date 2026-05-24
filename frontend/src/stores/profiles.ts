import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ProfileInfo } from '@/types'
import { apiClient } from '@/api'

export const useProfilesStore = defineStore('profiles', () => {
  const profiles = ref<ProfileInfo[]>([])

  async function fetchProfiles() {
    try {
      const res = await apiClient.get('/profiles') as any
      const data = res?.data?.profiles || res?.profiles || res?.data
      if (Array.isArray(data)) {
        profiles.value = data
      }
    } catch (e) {
      console.error('Error fetching profiles:', e)
    }
  }

  function getProfile(name: string): ProfileInfo | undefined {
    return profiles.value.find(p => p.name === name)
  }

  return {
    profiles,
    fetchProfiles,
    getProfile,
  }
})