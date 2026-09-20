import { useJarvis } from '../../store/JarvisContext'
import { MessageCircle } from 'lucide-react'

export default function AgentCommons() {
  const { peers } = useJarvis()

  return (
    <div className="hud-panel hud-chamfer p-3">
      <div className="flex items-center justify-between">
        <h3 className="text-[11px] tracking-widest text-hud-cyan/70">AGENT COMMONS - PEERS</h3>
        <span className="text-[10px] text-hud-muted">MODULES</span>
      </div>
      <div className="mt-2 space-y-2">
        {peers.map((peer) => (
          <div
            key={peer.id}
            className="flex items-center justify-between rounded-lg border border-hud-border/40 bg-hud-panel/60 px-3 py-2"
          >
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-hud-amber hud-glow-amber" />
              <span className="text-[11px] text-hud-cyan/80">{peer.name}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-[10px] text-hud-amber">{peer.status}</span>
              <span className="text-[10px] text-hud-muted">({peer.lastSeen})</span>
              <button className="rounded-full border border-hud-border/40 p-1 text-hud-cyan hover:text-white">
                <MessageCircle className="h-3 w-3" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
