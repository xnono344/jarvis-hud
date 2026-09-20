import { useRef, useEffect } from 'react'

export default function RadarSweep() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const size = 140
    canvas.width = size * dpr
    canvas.height = size * dpr
    canvas.style.width = `${size}px`
    canvas.style.height = `${size}px`
    ctx.scale(dpr, dpr)

    const cx = size / 2
    const cy = size / 2
    const maxR = size / 2 - 4
    let angle = 0
    let raf: number

    const draw = () => {
      ctx.clearRect(0, 0, size, size)

      ctx.strokeStyle = 'rgba(0,240,255,0.18)'
      ctx.lineWidth = 0.6
      for (let r = 10; r <= maxR; r += 14) {
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, Math.PI * 2)
        ctx.stroke()
      }
      for (let a = 0; a < Math.PI * 2; a += Math.PI / 4) {
        ctx.beginPath()
        ctx.moveTo(cx + Math.cos(a) * 6, cy + Math.sin(a) * 6)
        ctx.lineTo(cx + Math.cos(a) * maxR, cy + Math.sin(a) * maxR)
        ctx.stroke()
      }

      ctx.fillStyle = 'rgba(0,240,255,0.18)'
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.arc(cx, cy, maxR, angle - 0.7, angle, false)
      ctx.closePath()
      ctx.fill()

      ctx.strokeStyle = 'rgba(0,240,255,0.9)'
      ctx.lineWidth = 1.4
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.lineTo(cx + Math.cos(angle) * maxR, cy + Math.sin(angle) * maxR)
      ctx.stroke()

      angle = (angle + 0.022) % (Math.PI * 2)
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)

    return () => cancelAnimationFrame(raf)
  }, [])

  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-[10px] tracking-widest text-hud-cyan/70">PROXIMITY RADAR</span>
      <canvas ref={canvasRef} className="rounded-full border border-hud-border/40 hud-glow" />
    </div>
  )
}
