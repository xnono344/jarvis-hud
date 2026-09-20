export default function GrowthPipeline() {
  return (
    <div className="hud-panel hud-chamfer p-3">
      <h3 className="text-[11px] tracking-widest text-hud-cyan/70">GROWTH // PIPELINE</h3>
      <div className="mt-2 flex items-end gap-2">
        <div>
          <div className="text-2xl font-bold hud-text-glow">$15K</div>
          <div className="text-[10px] text-hud-muted">MRR / 12% monthly</div>
        </div>
        <div className="h-8 w-24 rounded-sm border border-hud-border/60 bg-hud-panel/60 p-1">
          <div className="h-full w-3/4 rounded-sm bg-gradient-to-r from-hud-cyan/40 to-hud-cyan/10" />
        </div>
      </div>
      <div className="mt-2 space-y-1 text-[11px]">
        <div className="flex items-center justify-between">
          <span className="text-hud-cyan/80">Frayze Growth (Cockpit)</span>
          <span className="rounded-full border border-hud-cyan/40 px-2 py-0.5 text-[10px] text-hud-cyan">ACTIVE</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-hud-cyan/80">South Shore Roof (The Roof App)</span>
          <span className="rounded-full border border-hud-amber/40 px-2 py-0.5 text-[10px] text-hud-amber">IN-PROGRESS</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-hud-cyan/80">Blue-Line Solutions</span>
          <span className="rounded-full border border-hud-crimson/40 px-2 py-0.5 text-[10px] text-hud-crimson">BLOCKED</span>
        </div>
      </div>
    </div>
  )
}
