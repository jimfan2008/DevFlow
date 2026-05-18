import { ref } from 'vue'
import { commentApi } from '@/api'
import type { CommentItem } from '@/types/api'

export function useCommentStore() {
  const comments = ref<CommentItem[]>([])
  const loading = ref(false)

  async function fetchComments(taskId: string) {
    loading.value = true
    try {
      const res = await commentApi.list(taskId)
      if (res.data) {
        comments.value = res.data
      }
    } finally {
      loading.value = false
    }
  }

  return { comments, loading, fetchComments }
}
