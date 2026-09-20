import { motion, useAnimation } from 'framer-motion'
import { useEffect } from 'react'
import { useJarvis } from '../../store/JarvisContext'
import OrbitNode from './OrbitNode'

const NODES = [
  { key: 'skills' as const, angle: -90 },
  { key: 'projects' as const, angle: -30 },
  { key: 'resources' as const, angle: 30 },
  { key: 'onTrack' as const, angle: 90 },
  { key: 'memory' as const, angle: 150 },
  { key: 'reference' as const, angle: 210 },
  { key: 'rules' as const, angle: 270 },
]

export default function OrbitalRing({ onSelectNode }: { onSelectNode: (key: string) => void }) {
  const { status, nodes } = useJarvis()
  const controls = useAnimation()

  useEffect(() => {
    const duration = status === 'thinking' ? 3 : status === 'speaking' ? 8 : 24
    controls.start({
      rotate: 360,
      transition: {
        duration,
        repeat: Infinity,
        ease: 'linear',
      },
    })
  }, [status, controls])

  return (
    <div className="relative flex items-center justify-center" style={{ width: 640, height: 640 }}>
      {/* Outer rotating ring container */}
      <motion.div animate={controls} className="absolute inset-0 hud-ring">
        {/* SVG Holographic rings and connectors */}
        <svg className="absolute inset-0 h-full w-full" viewBox="0 0 640 640">
          <defs>
            <radialGradient id="core-glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.5" />
              <stop offset="45%" stopColor="#00f0ff" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#00f0ff" stopOpacity="0" />
            </radialGradient>
            <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
              <path d="M 32 0 L 0 0 0 32" fill="none" stroke="rgba(0,240,255,0.08)" strokeWidth="0.5" />
            </pattern>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background grid */}
          <rect width="640" height="640" fill="url(#grid)" />

          {/* Core glow */}
          <circle cx="320" cy="320" r="300" fill="url(#core-glow)" />

          {/* Outer orbit ring - dashed */}
          <circle cx="320" cy="320" r="240" fill="none" stroke="rgba(0,240,255,0.25)" strokeWidth="1" strokeDasharray="16 12" />

          {/* Middle ring */}
          <circle cx="320" cy="320" r="180" fill="none" stroke="rgba(0,240,255,0.18)" strokeWidth="1" />

          {/* Inner ring */}
          <circle cx="320" cy="320" r="120" fill="none" stroke="rgba(0,240,255,0.3)" strokeWidth="1.5" />

          {/* Radar sonar rings inside core */}
          <circle cx="320" cy="320" r="90" fill="none" stroke="rgba(0,240,255,0.25)" strokeWidth="0.8" />
          <circle cx="320" cy="320" r="60" fill="none" stroke="rgba(0,240,255,0.2)" strokeWidth="0.8" />
          <circle cx="320" cy="320" r="30" fill="none" stroke="rgba(0,240,255,0.25)" strokeWidth="0.8" />

          {/* Cross lines */}
          <line x1="320" y1="220" x2="320" y2="420" stroke="rgba(0,240,255,0.12)" strokeWidth="0.8" />
          <line x1="220" y1="320" x2="420" y2="320" stroke="rgba(0,240,255,0.12)" strokeWidth="0.8" />

          {/* Radial connector lines to satellites */}
          {NODES.map(({ key, angle }) => {
            const rad = ((angle - 90) * Math.PI) / 180
            const x2 = 320 + Math.cos(rad) * 240
            const y2 = 320 + Math.sin(rad) * 240
            return (
              <line
                key={key}
                x1="320"
                y1="320"
                x2={x2.toFixed(2)}
                y2={y2.toFixed(2)}
                stroke="rgba(0,240,255,0.3)"
                strokeWidth="1"
                strokeDasharray="8 6"
              />
            )
          })}
        </svg>

        {/* Satellite nodes */}
        {NODES.map(({ key, angle }) => (
          <OrbitNode
            key={key}
            label={key}
            value={nodes[key]}
            angleDeg={angle}
            distance={240}
            onClick={() => onSelectNode(key)}
          />
        ))}
      </motion.div>

      {/* Center core with radar effect */}
      <div className="relative z-10 flex flex-col items-center justify-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 6, repeat: Infinity, ease: 'linear' }}
          className="absolute inset-0 flex items-center justify-center"
          style={{ width: 280, height: 280 }}
        >
          <div className="h-full w-full rounded-full"
               style={{
                 background: 'conic-gradient(from 0deg, transparent 0deg, rgba(0,240,255,0.25) 25deg, rgba(0,240,255,0.05) 50deg, transparent 60deg)',
                 filter: 'blur(8px)'
               }} />
        </motion.div>

        <div className="relative flex items-center justify-center rounded-full border border-hud-cyan/80 bg-hud-bg/80 px-10 py-8 backdrop-blur-md hud-glow"
             style={{ width: 220, height: 220 }}>
          {/* Inner radar sweep effect */}
          <div className="absolute inset-0 overflow-hidden rounded-full">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
              className="absolute inset-0"
            >
              <div className="h-full w-full rounded-full"
                   style={{
                     background: 'conic-gradient(from 0deg, transparent 0deg, rgba(0,240,255,0.35) 20deg, rgba(0,240,255,0.1) 40deg, transparent 50deg)'
                   }} />
            </motion.div>
          </div>

          {/* Center text */}
          <div className="relative z-10 flex flex-col items-center">
            <span className="text-4xl font-bold tracking-widest hud-text-glow" style={{ fontFamily: 'var(--font-family-tech)' }}>
              J.A.R.V.I.S
            </span>
            <span className="mt-2 text-xs tracking-[0.5em] text-hud-cyan/90 uppercase">Online</span>
            <span className="mt-4 text-2xl font-mono text-hud-cyan hud-text-glow tabular-nums">
              {new Date().toLocaleTimeString('en-US', { hour12: false })}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
