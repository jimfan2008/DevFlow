/**
 * DevFlow API 统一类型定义
 * 与后端 Pydantic Schema 保持严格一致
 */

// ==================== 统一响应 ====================

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T | null
  errors?: ValidationError[]
}

export interface PaginatedResponse<T> {
  code: number
  message: string
  data: T[]
  meta: PaginationMeta
}

export interface PaginationMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface ValidationError {
  field?: string
  message: string
  code?: string
}

// ==================== 认证模块 ====================

export interface RegisterRequest {
  username: string
  email: string
  password: string
  confirm_password: string
  display_name?: string
}

export interface LoginRequest {
  username?: string
  email?: string
  password: string
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface TokensResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UserProfile {
  id: string
  username: string
  email: string
  display_name: string
  role: 'admin' | 'member' | 'guest'
  avatar_url: string | null
  created_at: string
  updated_at?: string
  last_login?: string
  is_active?: boolean
}

export interface UserDetailResponse {
  id: string
  username: string
  email: string
  display_name: string
  role: string
  avatar_url: string | null
  last_login: string
  created_at: string
  is_active: boolean
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

export interface UpdateProfileRequest {
  display_name?: string
  avatar_url?: string
}

export interface LogoutRequest {
  refresh_token?: string
}

// ==================== 看板模块 ====================

export interface BoardColumn {
  id: string
  board_id: string
  name: string
  color: string
  position: number
  is_active: boolean
  task_count?: number
  created_at: string
}

export interface BoardCreateRequest {
  name: string
  description?: string
  columns?: ColumnCreateRequest[]
}

export interface BoardUpdateRequest {
  name?: string
  description?: string
}

export interface BoardListItem {
  id: string
  name: string
  description: string
  column_count: number
  task_count: number
  created_at: string
}

export interface BoardDetail {
  id: string
  name: string
  description: string
  columns: BoardColumn[]
  created_at: string
  updated_at: string
}

export interface ColumnCreateRequest {
  name: string
  color?: string
  position?: number
}

export interface ColumnUpdateRequest {
  name?: string
  color?: string
  position?: number
  is_active?: boolean
}

export interface ColumnReorderRequest {
  columns: { column_id: string; position: number }[]
}

// ==================== 任务模块 ====================

export interface TaskStatus {
  todo: 'todo'
  in_progress: 'in_progress'
  review: 'review'
  done: 'done'
}

export type TaskStatusValue = TaskStatus[keyof TaskStatus]

export interface TaskPriority {
  low: 'low'
  medium: 'medium'
  high: 'high'
  urgent: 'urgent'
}

export type TaskPriorityValue = TaskPriority[keyof TaskPriority]

export interface TaskBasic {
  id: string
  board_id: string
  column_id: string
  title: string
  status: TaskStatusValue
  priority: TaskPriorityValue
  assignee: { id: string; username: string; display_name: string } | null
  creator: { id: string; username: string; display_name: string }
  blocked: boolean
  due_date: string | null
  due_overdue: boolean
  comments_count: number
  attachments_count: number
  tags: string[]
  estimate_hours?: number | null
  created_at: string
  updated_at: string
}

export interface TaskFull extends TaskBasic {
  description: string
  assignee_id: string | null
  creator_id: string
  predecessors: TaskBrief[]
  successors: TaskBrief[]
  comments: CommentItem[]
  attachments: AttachmentItem[]
}

export interface TaskBrief {
  id: string
  title: string
  status: TaskStatusValue
}

export interface TaskCreateRequest {
  board_id: string
  column_id: string
  title: string
  description?: string
  status?: TaskStatusValue
  priority?: TaskPriorityValue
  assignee_id?: string | null
  due_date?: string | null
  tags?: string[]
  estimate_hours?: number | null
}

export interface TaskUpdateRequest {
  title?: string
  description?: string
  status?: TaskStatusValue
  priority?: TaskPriorityValue
  assignee_id?: string | null
  due_date?: string | null
  tags?: string[]
  estimate_hours?: number | null
}

export interface TaskBulkMoveRequest {
  moves: {
    task_id: string
    column_id: string
    position?: number
  }[]
}

export interface TaskBulkMoveResponse {
  moved_count: number
  blockeds: { task_id: string; reason: string }[]
}

export interface TaskSearchRequest {
  q: string
  board_id?: string
  assignee_id?: string
  status?: TaskStatusValue
  limit?: number
}

export interface TaskSearchResult {
  id: string
  title: string
  snippet: string
  board_id: string
  column_id: string
  status: TaskStatusValue
  assignee_id: string
}

export interface TaskSearchResponse {
  code: number
  message: string
  data: TaskSearchResult[]
}

// ==================== 评论模块 ====================

export interface CommentItem {
  id: string
  task_id: string
  user_id: string
  user: { id: string; username: string; display_name: string }
  content: string
  created_at: string
  updated_at: string
}

export interface CommentCreateRequest {
  content: string
}

// ==================== 附件模块 ====================

export interface AttachmentItem {
  id: string
  task_id: string
  filename: string
  file_path: string
  size: number
  mime_type: string
  created_at: string
}

export interface AttachmentCreateResponse {
  id: string
  task_id: string
  filename: string
  file_path: string
  size: number
  mime_type: string
  created_at: string
}

// ==================== 依赖模块 ====================

export interface DependencyCreateRequest {
  predecessor_id: string
}

export interface DependencyItem {
  id: string
  task_id: string
  predecessor: {
    id: string
    title: string
    status: TaskStatusValue
    column_name: string
  }
}

// ==================== 负载模块 ====================

export interface TasksByStatus {
  todo: number
  in_progress: number
  review: number
  done: number
}

export interface WorkloadMember {
  user_id: string
  username: string
  display_name: string
  total_tasks: number
  tasks_by_status: TasksByStatus
  total_estimate_hours: number
  completed_estimate_hours: number
  pending_estimate_hours: number
  completion_ratio: number
  avg_completion_rate: number
  overload: boolean
  underload: boolean
}

export interface WorkloadSummary {
  total_tasks: number
  total_members: number
  avg_tasks_per_member: number
  overloaded_members: number
  underloaded_members: number
}

export interface WorkloadResponse {
  board_id: string
  period: { start: string; end: string }
  members: WorkloadMember[]
  board_summary: WorkloadSummary
}

// ==================== 收件箱模块 ====================

export interface InboxNotification {
  id: string
  user_id: string
  type: NotificationType
  title: string
  body: string
  task_id?: string
  board_id?: string
  actor: { id: string; username: string; display_name: string }
  is_read: boolean
  created_at: string
}

export type NotificationType =
  | 'assigned'
  | 'comment'
  | 'status_change'
  | 'due_reminder'
  | 'mention'

export interface InboxListResponse {
  code: number
  message: string
  data: InboxNotification[]
  meta: PaginationMeta & { unread_count: number }
}

export interface UnreadCountResponse {
  code: number
  message: string
  data: { unread_count: number }
}

// ==================== 用户模块 ====================

export interface UserListItem {
  id: string
  username: string
  display_name: string
  role: string
  is_active: boolean
  avatar_url: string | null
}
