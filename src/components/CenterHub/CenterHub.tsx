import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import OrbitalRing from './OrbitalRing'
import RadarSweep from './RadarSweep'
import AudioSynth from './AudioSynth'

const NODE_DETAILS: Record<string, { title: string; items: string[] }> = {
  skills: {
    title: 'SKILLS',
    items: ['WebSocket streaming', 'REST API orchestration', 'Telemetry ingestion', 'Multi-agent mesh', 'Canvas visualizations', 'Voice synth synthesis', 'Weather integration', 'Memory indexing'],
  },
  rules: {
    title: 'RULES',
    items: ['Zero external telemetry leakage', 'Hardware-accelerated only', 'Wayland-first rendering', 'Backend-first API contracts', 'No PII in logs', 'Graceful telemetry fallback', 'Framer Motion GPU layers', 'Tailwind utility-first'],
  },
  memory: {
    title: 'MEMORY',
    items: ['User preferences cached', 'Session uptime tracked', 'Agent state persisted', 'Telemetry rolling window', 'Task completion history', 'Peer agent status cache', 'Weather cache (5 min)', 'Node selection history'],
  },
  reference: {
    title: 'REFERENCE',
    items: ['Open-Meteo docs', 'Framer Motion API', 'React 19 patterns', 'Tailwind v4 config', 'Vite HMR guide', 'Canvas best practices', 'Wayland HiDPI docs', 'nvidia-smi reference'],
  },
  projects: {
    title: 'PROJECTS',
    items: ['jarvis-hud (this)', 'Second Brain CLI', 'Frayze Cockpit', 'The Roof App', 'Blue-Line Solutions', 'South Shore Roofing', 'Agent Mesh P2P', 'MCP Server Pack'],
  },
  resources: {
    title: 'RESOURCES',
    items: ['Open-Meteo API', 'Telemetry middleware', 'MCP servers (6)', 'Local GPU driver', 'Hyprland socket', 'Node.js runtime'],
  },
  onTrack: {
    title: 'ON TRACK',
    items: ['Core ring animation', 'Telemetry polling', 'Task state sync', 'Peer status watch', 'Activity log stream', 'Audio synth render', 'Radar sweep loop', 'Weather polling'],
  },
}

export default function CenterHub() {
  const [selected, setSelected] = useState<string | null>(null)

  return (
    <div className="relative flex flex-col items-center justify-center">
      <div className="mb-4 rounded-full border border-hud-amber/50 bg-hud-panel/70 px-5 py-1.5 backdrop-blur-md hud-glow-amber">
        <span className="text-[11px] tracking-widest text-hud-amber uppercase">[ FOCUS NOW ] cold - follow up.</span>
      </div>

      <OrbitalRing onSelectNode={setSelected} />

      <div className="mt-6 flex items-center gap-8">
        <RadarSweep />
        <AudioSynth />
      </div>

      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="absolute bottom-0 left-1/2 z-50 w-80 -translate-x-1/2 translate-y-1/2 rounded-xl border border-hud-border/60 bg-hud-panel/90 p-4 backdrop-blur-xl hud-glow"
          >
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm tracking-widest text-hud-amber">{NODE_DETAILS[selected]?.title}</h3>
              <button onClick={() => setSelected(null)} className="text-hud-muted hover:text-hud-cyan text-xs">
                CLOSE
              </button>
            </div>
            <ul className="space-y-1">
              {NODE_DETAILS[selected]?.items.map((item) => (
                <li key={item} className="text-xs text-hud-cyan/80">
                  › {item}
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
