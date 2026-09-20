import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useJarvis } from '../../store/JarvisContext'
import { Send, Mic, Square } from 'lucide-react'

export default function CommandConsole() {
  const { sendMessage, sendAudio, status, messages } = useJarvis()
  const [input, setInput] = useState('')
  const [recording, setRecording] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const recordingRef = useRef(false)
  const chunksRef = useRef<Blob[]>([])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async () => {
    if (!input.trim()) return
    await sendMessage(input)
    setInput('')
  }

  // Push-to-talk: click to record, click again to send the utterance.
  // Also triggered by the global hotkey via the 'jarvis:mic-toggle' event.
  const toggleRecording = useCallback(async () => {
    if (recordingRef.current) {
      recorderRef.current?.stop()
      return
    }
    recordingRef.current = true
    setRecording(true)
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      recordingRef.current = false
      setRecording(false)
      return
    }
    try {
      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm'
      const recorder = new MediaRecorder(stream, { mimeType: mime })
      chunksRef.current = []
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = () => {
        recordingRef.current = false
        setRecording(false)
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        chunksRef.current = []
        if (blob.size > 0) sendAudio(blob)
      }
      recorderRef.current = recorder
      recorder.start()
    } catch {
      recordingRef.current = false
      setRecording(false)
      stream.getTracks().forEach((t) => t.stop())
    }
  }, [sendAudio])

  useEffect(() => {
    const onHotkey = () => {
      void toggleRecording()
    }
    window.addEventListener('jarvis:mic-toggle', onHotkey)
    return () => window.removeEventListener('jarvis:mic-toggle', onHotkey)
  }, [toggleRecording])

  return (
    <div className="hud-panel hud-chamfer flex flex-col overflow-hidden">
      <div className="flex-1 space-y-1.5 overflow-y-auto p-3">
        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className={`text-[11px] leading-relaxed ${
                msg.role === 'user' ? 'text-hud-amber' : 'text-hud-cyan/80'
              }`}
            >
              <span className="text-hud-muted">
                [{new Date(msg.timestamp).toLocaleTimeString('en-US', { hour12: false })}]
              </span>{' '}
              <span className="font-semibold">{msg.role === 'user' ? 'DENIS' : 'J.A.R.V.I.S'}:</span>{' '}
              <span className="whitespace-pre-wrap">{msg.content}</span>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      <div className="flex items-center gap-2 border-t border-hud-border/40 p-2">
        <span className="text-hud-muted">🔒</span>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          placeholder={status === 'thinking' ? 'J.A.R.V.I.S is thinking...' : 'Awaiting your command, sir...'}
          disabled={status === 'thinking'}
          className="flex-1 bg-transparent text-[11px] text-hud-cyan placeholder:text-hud-muted outline-none disabled:opacity-50"
        />
        <button
          onClick={toggleRecording}
          title={recording ? 'Stop and send' : 'Speak to J.A.R.V.I.S'}
          className={`rounded-lg border px-3 py-1.5 text-[11px] transition ${
            recording
              ? 'border-hud-crimson/60 text-hud-crimson hud-glow-crimson animate-pulse'
              : 'border-hud-amber/40 text-hud-amber hover:bg-hud-amber/10 hud-glow-amber'
          }`}
        >
          {recording ? <Square className="h-3.5 w-3.5" /> : <Mic className="h-3.5 w-3.5" />}
        </button>
        <button
          onClick={handleSubmit}
          disabled={status === 'thinking'}
          className="rounded-lg border border-hud-cyan/40 px-3 py-1.5 text-[11px] text-hud-cyan hover:bg-hud-cyan/10 hud-glow disabled:opacity-50"
        >
          <Send className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}
