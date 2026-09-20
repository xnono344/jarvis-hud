export default function CRMStats() {
  return (
    <div className="hud-panel hud-chamfer p-3">
      <div className="flex items-center justify-between">
        <h3 className="text-[11px] tracking-widest text-hud-cyan/70">FRAYZE CRM : LIVE</h3>
        <span className="text-[10px] text-hud-muted">GML LIVE</span>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2">
        <div className="rounded-lg border border-hud-border/40 bg-hud-panel/60 p-2">
          <div className="text-[10px] text-hud-muted">CONTACTS</div>
          <div className="text-xl font-bold hud-text-glow">5,969</div>
          <div className="text-[10px] text-hud-cyan/70">2,142 in CRM</div>
        </div>
        <div className="rounded-lg border border-hud-crimson/40 bg-hud-panel/60 p-2">
          <div className="text-[10px] text-hud-crimson">OUTREACH TARGETS</div>
          <div className="text-xl font-bold text-hud-crimson hud-glow-crimson">128</div>
          <div className="text-[10px] text-hud-crimson/70">Active campaigns</div>
        </div>
        <div className="rounded-lg border border-hud-border/40 bg-hud-panel/60 p-2">
          <div className="text-[10px] text-hud-muted">NEW LEADS</div>
          <div className="text-xl font-bold text-hud-amber hud-text-glow-amber">24</div>
          <div className="text-[10px] text-hud-amber/70">This week</div>
        </div>
        <div className="rounded-lg border border-hud-border/40 bg-hud-panel/60 p-2">
          <div className="text-[10px] text-hud-muted">GSM / AC</div>
          <div className="text-xl font-bold hud-text-glow">38</div>
          <div className="text-[10px] text-hud-cyan/70">Connected</div>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-2 border-t border-hud-border/40 pt-2 text-[10px] text-hud-muted">
        <span>820 SPOKANE 360</span>
        <span className="ml-auto flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 hud-glow" />
          <span className="text-emerald-400">LIVE</span>
        </span>
      </div>
    </div>
  )
}
