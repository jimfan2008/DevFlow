<template>
  <div class="acceptance-view">
    <div class="acceptance-view__header">
      <h2 class="acceptance-view__title">验收报告</h2>
      <el-select v-model="statusFilter" placeholder="状态筛选" style="width: 140px" clearable @change="handleFilterChange">
        <el-option label="全部" value="" />
        <el-option label="待审核" value="pending" />
        <el-option label="已通过" value="approved" />
        <el-option label="已驳回" value="rejected" />
      </el-select>
    </div>

    <el-table :data="store.reports" stripe v-loading="store.loading">
      <el-table-column prop="task_id" label="任务ID" width="120" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'" size="small">
            {{ row.status === 'approved' ? '已通过' : row.status === 'rejected' ? '已驳回' : '待审核' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="审核人" width="120">
        <template #default="{ row }">{{ row.reviewer?.display_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" size="small" type="success" @click="handleApprove(row.id)">通过</el-button>
          <el-button v-if="row.status === 'pending'" size="small" type="danger" @click="showRejectDialog(row)">驳回</el-button>
          <el-button size="small" @click="showReportDetail(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="rejectDialogVisible" title="驳回验收" width="480px">
      <el-form label-width="80px">
        <el-form-item label="问题明细" required>
          <el-input v-model="rejectForm.issues" type="textarea" :rows="4" placeholder="每行一个问题" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="rejectForm.comment" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="store.loading" @click="handleReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailDialogVisible" title="验收报告详情" width="600px">
      <template v-if="store.currentReport">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="任务ID">{{ store.currentReport.task_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ store.currentReport.status }}</el-descriptions-item>
          <el-descriptions-item label="审核人">{{ store.currentReport.reviewer?.display_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(store.currentReport.created_at) }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="store.currentReport.issues?.length" style="margin-top: 16px">
          <strong>问题明细:</strong>
          <ul><li v-for="issue in store.currentReport.issues" :key="issue">{{ issue }}</li></ul>
        </div>
        <div v-if="store.currentReport.suggestions?.length" style="margin-top: 12px">
          <strong>建议:</strong>
          <ul><li v-for="s in store.currentReport.suggestions" :key="s">{{ s }}</li></ul>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAcceptanceStore } from '@/stores/useAcceptanceStore'
import type { AcceptanceReport } from '@/types/api'

const store = useAcceptanceStore()
const statusFilter = ref('')
const rejectDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const rejectForm = ref({ reportId: '', issues: '', comment: '' })

onMounted(() => {
  store.fetchReports()
})

function handleFilterChange() {
  store.fetchReports(undefined, statusFilter.value || undefined)
}

async function handleApprove(reportId: string) {
  const result = await store.approveReport(reportId)
  if (result) {
    ElMessage.success('验收已通过')
    store.fetchReports(undefined, statusFilter.value || undefined)
  }
}

function showRejectDialog(report: AcceptanceReport) {
  rejectForm.value = { reportId: report.id, issues: '', comment: '' }
  rejectDialogVisible.value = true
}

async function handleReject() {
  const issues = rejectForm.value.issues.split('\n').filter(i => i.trim())
  if (!issues.length) return ElMessage.warning('请输入问题明细')
  const result = await store.rejectReport(rejectForm.value.reportId, issues, rejectForm.value.comment || undefined)
  if (result) {
    ElMessage.success('验收已驳回')
    rejectDialogVisible.value = false
    store.fetchReports(undefined, statusFilter.value || undefined)
  }
}

async function showReportDetail(report: AcceptanceReport) {
  await store.fetchReportDetail(report.id)
  detailDialogVisible.value = true
}

function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN')
}
</script>

<style lang="scss" scoped>
.acceptance-view {
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
  }
}
</style>
