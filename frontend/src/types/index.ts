export interface Message {
  id: string
  group_id: string
  sender: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  is_streaming: boolean
  metadata?: Record<string, unknown>
}

export interface MeetingAgendaItem {
  title: string
  description: string
  speakers: string[]
  timebox_min: number
  per_speaker_min: number
  expected_outputs: string[]
}

export interface MeetingState {
  isActive: boolean
  topic: string
  hostAgent: string
  participants: string[]
  agenda: MeetingAgendaItem[]
  currentPhase: string
  currentSpeaker: string | null
  currentAgendaIndex: number
  minutes: string
}

export interface MeetingOutcome {
  id: string
  meeting_topic: string
  host_agent: string
  decisions: { description: string; owner: string }[]
  todos: { description: string; assignee: string; deadline: string }[]
  risks: { description: string; mitigation: string }[]
  open_issues: { description: string; next_step: string }[]
}

export interface TaskItem {
  id: string
  group_id: string
  meeting_id?: string
  assignee: string
  description: string
  deadline?: string
  status: string
  created_at: string
  completed_at?: string
  result?: string
}

export interface GroupInfo {
  id: string
  name: string
  description?: string
  members: string[]
  host_agent?: string
  mode: string
  created_at: string
}

export interface ProfileInfo {
  name: string
  is_running: boolean
  model_default?: string
  model_provider?: string
  gateway_port?: number
  personality?: string
  config_path: string
}

export interface WsMessage {
  type: string
  group_id?: string
  message?: Partial<Message>
  profile_name?: string
  status?: string
  topic?: string
  host_agent?: string
  participants?: string[]
  phase?: string
  description?: string
  agenda?: MeetingAgendaItem[]
  speaker?: string
  content?: string
  message_id?: string
  error?: string
  minutes?: string
  meeting_outcome?: MeetingOutcome
  task?: TaskItem
  data?: string
}