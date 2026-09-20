import { motion } from 'framer-motion'

type NodeKey = 'skills' | 'rules' | 'memory' | 'reference' | 'projects' | 'resources' | 'onTrack'

const NODES: Record<NodeKey, { label: string; color: 'cyan' | 'amber' | 'crimson' }> = {
  skills: { label: 'SKILLS', color: 'cyan' },
  rules: { label: 'RULES', color: 'amber' },
  memory: { label: 'MEMORY', color: 'cyan' },
  reference: { label: 'REFERENCE', color: 'amber' },
  projects: { label: 'PROJECTS', color: 'cyan' },
  resources: { label: 'RESOURCES', color: 'amber' },
  onTrack: { label: 'ON TRACK', color: 'crimson' },
}

const colorMap = {
  cyan: 'text-hud-cyan border-hud-cyan/60 shadow-[0_0_20px_rgba(0,240,255,0.35)]',
  amber: 'text-hud-amber border-hud-amber/60 shadow-[0_0_20px_rgba(255,184,0,0.35)]',
  crimson: 'text-hud-crimson border-hud-crimson/60 shadow-[0_0_20px_rgba(255,69,96,0.35)]',
}

interface Props {
  label: NodeKey
  value: number
  angleDeg: number
  distance: number
  onClick: () => void
}

export default function OrbitNode({ label, value, angleDeg, distance, onClick }: Props) {
  const info = NODES[label]
  const angleRad = ((angleDeg - 90) * Math.PI) / 180
  const x = Math.cos(angleRad) * distance
  const y = Math.sin(angleRad) * distance

  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.12 }}
      whileTap={{ scale: 0.94 }}
      style={{ x, y }}
      className={`absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-1 rounded-full border px-4 py-2 backdrop-blur-md bg-hud-bg/80 ${colorMap[info.color]}`}
    >
      <span className="text-[11px] font-bold tracking-widest uppercase">{info.label}</span>
      <span className="text-xl font-bold leading-none tabular-nums">{value}</span>
    </motion.button>
  )
}
