import { useJarvis } from '../../store/JarvisContext'
import { useMemo } from 'react'

export default function ActivityPulse() {
  const { logs } = useJarvis()

  const latest = useMemo(() => logs.slice(0, 7), [logs])

  return (
    <div className="hud-panel hud-chamfer p-3">
      <div className="flex items-center justify-between">
        <h3 className="text-[11px] tracking-widest text-hud-cyan/70">ACTIVITY // PULSE</h3>
        <span className="text-[10px] text-hud-muted">operator-console-biz-monitor</span>
      </div>
      <div className="mt-2 space-y-1.5">
        {latest.map((log) => (
          <div key={log.id} className="flex items-start gap-2 text-[11px]">
            <span className="mt-px shrink-0 text-hud-muted">{log.time}</span>
            <span className="text-hud-amber">{log.source}:</span>
            <span className="text-hud-cyan/80">{log.message}</span>
          </div>
        ))}
      </div>
      <div className="mt-2 border-t border-hud-border/40 pt-1 text-[10px] text-hud-muted">WORKLOG</div>
    </div>
  )
}
