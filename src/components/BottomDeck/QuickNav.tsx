import { useJarvis } from '../../store/JarvisContext'
import { Lightbulb, Hammer, Box, Plane, Music, Focus } from 'lucide-react'

const MODES = [
  { label: 'INSIGHTS', icon: Lightbulb, color: 'cyan' as const },
  { label: 'BUILD PLAN', icon: Hammer, color: 'amber' as const },
  { label: 'MODULES', icon: Box, color: 'cyan' as const },
  { label: 'TRIP', icon: Plane, color: 'amber' as const },
  { label: 'MUSIC', icon: Music, color: 'emerald' as const },
  { label: 'FOCUS', icon: Focus, color: 'amber' as const },
]

export default function QuickNav() {
  const { setStatus } = useJarvis()

  const handleClick = (_label: string) => {
    setStatus('thinking')
    setTimeout(() => setStatus('idle'), 2000)
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] tracking-widest text-hud-muted">J.A.R.V.I.S</span>
      {MODES.map((mode) => (
        <button
          key={mode.label}
          onClick={() => handleClick(mode.label)}
          className={`rounded-lg border px-3 py-1.5 text-[11px] tracking-wider transition ${
            mode.color === 'cyan'
              ? 'border-hud-cyan/40 text-hud-cyan hover:bg-hud-cyan/10 hud-glow'
              : mode.color === 'amber'
                ? 'border-hud-amber/40 text-hud-amber hover:bg-hud-amber/10 hud-glow-amber'
                : 'border-emerald-400/40 text-emerald-400 hover:bg-emerald-400/10'
          }`}
        >
          {mode.label}
        </button>
      ))}
    </div>
  )
}
