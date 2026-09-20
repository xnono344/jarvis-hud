export type JarvisStatus = 'idle' | 'thinking' | 'speaking' | 'offline'

export interface SystemMetrics {
  cpu: number
  ram: number
  gpu: number
  uptime: string
}

export interface TaskItem {
  id: string
  title: string
  tag: 'CURRENT' | 'IN-PROGRESS' | 'INTERNAL' | 'BLOCKED'
  completed: boolean
}

export interface LogItem {
  id: string
  time: string
  source: string
  message: string
}

export interface AgentPeer {
  id: string
  name: string
  status: 'awaiting reply' | 'online' | 'offline'
  lastSeen: string
}

export interface JarvisNodes {
  skills: number
  rules: number
  memory: number
  reference: number
  projects: number
  resources: number
  onTrack: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface JarvisState {
  status: JarvisStatus
  metrics: SystemMetrics
  nodes: JarvisNodes
  tasks: TaskItem[]
  logs: LogItem[]
  peers: AgentPeer[]
  messages: ChatMessage[]
  sendMessage: (prompt: string) => Promise<void>
  sendAudio: (blob: Blob) => void
  setStatus: (status: JarvisStatus) => void
  toggleTask: (id: string) => void
  addTask: (title: string, tag: TaskItem['tag']) => void
}
