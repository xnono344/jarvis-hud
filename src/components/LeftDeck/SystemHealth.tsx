import { useJarvis } from '../../store/JarvisContext'
import { Cpu, HardDrive, Gauge } from 'lucide-react'

export default function SystemHealth() {
  const { metrics } = useJarvis()
  const score = 100

  const bars = [
    { label: 'CPU', value: metrics.cpu, icon: Cpu },
    { label: 'RAM', value: metrics.ram, icon: HardDrive },
    { label: 'GPU', value: metrics.gpu, icon: Gauge },
  ]

  return (
    <div className="hud-panel hud-chamfer p-3">
      <h3 className="text-[11px] tracking-widest text-hud-cyan/70">SYSTEM HEALTH</h3>
      <div className="mt-2 flex items-center gap-3">
        <div className="text-4xl font-bold hud-text-glow">{score}<span className="text-lg text-hud-cyan/70">/100</span></div>
        <span className="rounded-full border border-emerald-400/50 px-2 py-0.5 text-[10px] text-emerald-400">EXCELLENT</span>
      </div>
      <div className="mt-3 space-y-2">
        {bars.map((bar) => (
          <div key={bar.label}>
            <div className="flex items-center justify-between text-[10px] text-hud-muted">
              <span className="flex items-center gap-1">
                <bar.icon className="h-3 w-3" />
                {bar.label}
              </span>
              <span className="text-hud-cyan">{bar.value}%</span>
            </div>
            <div className="mt-1 h-1.5 w-full rounded-full bg-hud-panel/80">
              <div
                className="h-full rounded-full bg-hud-cyan hud-glow"
                style={{ width: `${bar.value}%`, transition: 'width 0.6s ease' }}
              />
            </div>
          </div>
        ))}
      </div>
      <p className="mt-2 text-[10px] text-hud-muted">
        [ 3 connected services: Deploy (local-testing), docker: app-local-testing ]
      </p>
    </div>
  )
}
