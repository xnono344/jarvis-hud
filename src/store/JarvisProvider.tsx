import { useState, useCallback, useEffect, useRef } from 'react'
import type { JarvisState, JarvisStatus, TaskItem, LogItem, AgentPeer, ChatMessage } from './types'
import { JarvisContext } from './JarvisContext'

// Production follows the served page; development can override a custom port.
const BACKEND_HTTP_URL = import.meta.env.VITE_BACKEND_HTTP_URL || (
  import.meta.env.DEV ? `http://${window.location.hostname || '127.0.0.1'}:8766` : window.location.origin
)

const now = new Date()
const timeLabel = (d: Date) =>
  d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })

const initialTasks: TaskItem[] = [
  { id: '1', title: 'Build Phase 2 inventory e...', tag: 'CURRENT', completed: true },
  { id: '2', title: 'Finish onboarding setup', tag: 'IN-PROGRESS', completed: false },
  { id: '3', title: 'Wire live GML tiles into...', tag: 'INTERNAL', completed: false },
  { id: '4', title: 'Swap-8-embedded-submodu...', tag: 'INTERNAL', completed: false },
]

const initialLogs: LogItem[] = [
  { id: '1', time: timeLabel(new Date(now.getTime() - 1000 * 60 * 10)), source: 'scaffold', message: 'Training pipeline initialized' },
  { id: '2', time: timeLabel(new Date(now.getTime() - 1000 * 60 * 25)), source: 'evolve', message: 'Cross-link agent memory graph' },
  { id: '3', time: timeLabel(new Date(now.getTime() - 1000 * 60 * 38)), source: 'merge', message: 'Client work-logs merged' },
  { id: '4', time: timeLabel(new Date(now.getTime() - 1000 * 60 * 52)), source: 'jarvis', message: 'Fold GML comms channel' },
  { id: '5', time: timeLabel(new Date(now.getTime() - 1000 * 60 * 65)), source: 'jarvis', message: 'De-squish + merge agent sessions' },
  { id: '6', time: timeLabel(new Date(now.getTime() - 1000 * 60 * 80)), source: 'operator', message: 'Add Frayze company log entry' },
  { id: '7', time: timeLabel(new Date(now.getTime() - 1000 * 60 * 95)), source: 'operator', message: 'Make client WORKLOG.md accessible' },
]

const initialPeers: AgentPeer[] = [
  { id: '1', name: 'jimbo', status: 'awaiting reply', lastSeen: '1 min ago' },
  { id: '2', name: 'pathbot', status: 'awaiting reply', lastSeen: '25 sec ago' },
]

export function JarvisProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<JarvisStatus>('idle')
  const [metrics, setMetrics] = useState({
    cpu: 24,
    ram: 48,
    gpu: 12,
    uptime: '00:21:16',
  })
  const [nodes] = useState({
    skills: 36,
    rules: 17,
    memory: 17,
    reference: 14,
    projects: 13,
    resources: 6,
    onTrack: 12,
  })
  const [tasks, setTasks] = useState<TaskItem[]>(initialTasks)
  const [logs, _setLogs] = useState<LogItem[]>(initialLogs)
  const [peers, _setPeers] = useState<AgentPeer[]>(initialPeers)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Voice playback: base64 MP3 from the backend -> <audio>, driving the
  // 'speaking' state (AudioSynth visualizes it). Text is already on screen,
  // so a blocked/failed play() only skips audio, never the answer.
  const playAudio = useCallback((b64: string, mime: string) => {
    try {
      audioRef.current?.pause()
    } catch {
      /* ignore */
    }
    const audio = new Audio(`data:${mime || 'audio/mpeg'};base64,${b64}`)
    audioRef.current = audio
    setStatus('speaking')
    const done = () => {
      if (audioRef.current === audio) {
        audioRef.current = null
        setStatus('idle')
      }
    }
    audio.onended = done
    audio.onerror = done
    audio.play().catch(done)
  }, [])

  // Backend link: single WebSocket to the local Python bridge.
  // Only this effect + sendMessage/sendAudio talk to the backend; nothing else changed.
  useEffect(() => {
    let closed = false
    let retry: ReturnType<typeof setTimeout>
    const controller = new AbortController()

    const connect = async () => {
      if (closed) return
      let ws: WebSocket
      try {
        // Refresh the credential on every reconnect (backend restarts rotate it).
        const response = await fetch(new URL('/api/session', BACKEND_HTTP_URL), {
          cache: 'no-store', signal: controller.signal,
        })
        if (!response.ok) throw new Error('Local session unavailable')
        const session = await response.json() as { token: string; ws_port: number; ws_path: string }
        if (closed) return
        const url = new URL(BACKEND_HTTP_URL)
        url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
        url.port = String(session.ws_port)
        url.pathname = session.ws_path
        url.search = ''
        url.hash = ''
        ws = new WebSocket(url, ['jarvis', session.token])
      } catch {
        if (!closed) retry = setTimeout(() => { void connect() }, 3000)
        return
      }
      wsRef.current = ws

      ws.onmessage = (event) => {
        let msg: { type: string; payload?: Record<string, unknown> }
        try {
          msg = JSON.parse(event.data as string)
        } catch {
          return
        }
        const payload = (msg.payload ?? {}) as Record<string, unknown>
        switch (msg.type) {
          case 'chat:response': {
            const message = payload.message as ChatMessage
            if (message) setMessages((m) => [...m, message])
            setStatus((payload.status as JarvisStatus) ?? 'idle')
            break
          }
          case 'chat:transcript': {
            // Mic speech transcribed by the backend — show it as the user bubble.
            const message = payload.message as ChatMessage
            if (message) setMessages((m) => [...m, message])
            break
          }
          case 'audio:play': {
            const b64 = payload.audio as string
            if (b64) playAudio(b64, (payload.mime as string) ?? 'audio/mpeg')
            break
          }
          case 'mic:toggle':
            // Global hotkey path (POST /api/mic) — hand to CommandConsole.
            window.dispatchEvent(new CustomEvent('jarvis:mic-toggle'))
            break
          case 'status:change':
            // Don't let a stale 'idle' stomp active speech playback.
            if (payload.status === 'idle' && audioRef.current) break
            setStatus((payload.status as JarvisStatus) ?? 'idle')
            break
          case 'telemetry:update':
            setMetrics((prev) => ({
              ...prev,
              cpu: (payload.cpu as number) ?? prev.cpu,
              ram: (payload.ram as number) ?? prev.ram,
              gpu: (payload.gpu as number) ?? prev.gpu,
            }))
            break
          case 'tool:call': {
            // Destructive-action confirmation. Minimal native dialog for MVP;
            // replace with a HUD modal later without touching the protocol.
            const confirmed = window.confirm(
              String(payload.description ?? `Confirm action ${(payload.call_id as string) ?? ''}?`),
            )
            if (ws.readyState !== WebSocket.OPEN) break
            ws.send(
              JSON.stringify({
                type: 'tool:confirm',
                payload: { call_id: payload.call_id, confirmed },
              }),
            )
            break
          }
          case 'tool:result':
          case 'notification':
            break
          default:
            break
        }
      }

      ws.onclose = () => {
        if (wsRef.current === ws) wsRef.current = null
        if (!closed) retry = setTimeout(() => { void connect() }, 3000)
      }
      ws.onerror = () => ws.close()
    }

    // Unlock browser audio on first interaction so replies can auto-play.
    const unlock = () => {
      try {
        const Ctx =
          window.AudioContext ??
          (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
        if (Ctx) {
          const ctx = new Ctx()
          void ctx.resume().catch(() => undefined)
          ctx.close().catch(() => undefined)
        }
      } catch {
        /* ignore */
      }
    }
    window.addEventListener('pointerdown', unlock, { once: true })
    window.addEventListener('keydown', unlock, { once: true })

    void connect()
    return () => {
      closed = true
      controller.abort()
      clearTimeout(retry)
      window.removeEventListener('pointerdown', unlock)
      window.removeEventListener('keydown', unlock)
      wsRef.current?.close()
      wsRef.current = null
      try {
        audioRef.current?.pause()
      } catch {
        /* ignore */
      }
      audioRef.current = null
    }
  }, [playAudio])

  const sendMessage = useCallback(async (prompt: string) => {
    const text = prompt.trim()
    if (!text) return
    const ws = wsRef.current
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: Date.now(),
    }
    setMessages((m) => [...m, userMsg])
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      setStatus('offline')
      setMessages((m) => [
        ...m,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Backend offline — start it with `python backend/main.py` from the project root.',
          timestamp: Date.now(),
        },
      ])
      setStatus('idle')
      return
    }
    setStatus('thinking')
    try {
      audioRef.current?.pause()
    } catch {
      /* ignore */
    }
    audioRef.current = null
    ws.send(
      JSON.stringify({
        type: 'chat:message',
        payload: { prompt: text, message_id: userMsg.id },
      }),
    )
  }, [])

  // Mic utterance -> backend STT -> normal chat flow (transcript + reply).
  const sendAudio = useCallback((blob: Blob) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      setStatus('offline')
      setMessages((m) => [
        ...m,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Backend offline — start it with `python backend/main.py` from the project root.',
          timestamp: Date.now(),
        },
      ])
      setStatus('idle')
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = String(reader.result ?? '')
      const b64 = dataUrl.includes(',') ? dataUrl.split(',')[1] : dataUrl
      if (!b64) return
      try {
        audioRef.current?.pause()
      } catch {
        /* ignore */
      }
      audioRef.current = null
      setStatus('thinking')
      ws.send(
        JSON.stringify({
          type: 'audio:input',
          payload: {
            audio: b64,
            mime: blob.type || 'audio/webm',
            message_id: Date.now().toString(),
          },
        }),
      )
    }
    reader.readAsDataURL(blob)
  }, [])

  const toggleTask = useCallback((id: string) => {
    setTasks((t) => t.map((task) => (task.id === id ? { ...task, completed: !task.completed } : task)))
  }, [])

  const addTask = useCallback((title: string, tag: TaskItem['tag']) => {
    setTasks((t) => [...t, { id: Date.now().toString(), title, tag, completed: false }])
  }, [])

  const value: JarvisState = {
    status,
    metrics,
    nodes,
    tasks,
    logs,
    peers,
    messages,
    sendMessage,
    sendAudio,
    setStatus,
    toggleTask,
    addTask,
  }

  return <JarvisContext.Provider value={value}>{children}</JarvisContext.Provider>
}
