import { useRef, useEffect } from 'react'
import { useJarvis } from '../../store/JarvisContext'

export default function AudioSynth() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const { status } = useJarvis()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const width = 200
    const height = 56
    canvas.width = width * dpr
    canvas.height = height * dpr
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
    ctx.scale(dpr, dpr)

    let offset = 0
    let raf: number

    const draw = () => {
      ctx.clearRect(0, 0, width, height)
      ctx.strokeStyle = 'rgba(0,240,255,0.9)'
      ctx.lineWidth = 1.2
      ctx.beginPath()

      const amplitude = status === 'thinking' ? 20 : status === 'speaking' ? 14 : 7
      const frequency = status === 'thinking' ? 0.09 : 0.05

      for (let x = 0; x < width; x++) {
        const y = height / 2 + Math.sin(x * frequency + offset) * amplitude * Math.sin(x / width * Math.PI)
        if (x === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.stroke()

      offset += status === 'thinking' ? 0.12 : 0.05
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)

    return () => cancelAnimationFrame(raf)
  }, [status])

  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-[10px] tracking-widest text-hud-cyan/70">VOICE SYNTH</span>
      <canvas ref={canvasRef} className="border border-hud-border/40 hud-glow rounded-sm" />
    </div>
  )
}
