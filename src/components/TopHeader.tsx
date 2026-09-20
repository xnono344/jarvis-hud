import { useEffect, useState } from 'react'
import { Thermometer, Activity } from 'lucide-react'
import { useJarvis } from '../store/JarvisContext'
import { fetchWeather } from '../services/weatherService'

export default function TopHeader() {
  const { metrics } = useJarvis()
  const [weather, setWeather] = useState<{ tempC: number; condition: string; location: string } | null>(null)
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    fetchWeather().then(setWeather)
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const time = now.toLocaleTimeString('en-US', { hour12: false })
  const date = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

  return (
    <header className="flex items-center justify-between px-5 py-2 border-b border-hud-border/60 bg-hud-panel/40 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <span className="h-2.5 w-2.5 rounded-full bg-hud-cyan hud-glow" />
        <span className="text-xs tracking-widest text-hud-cyan/80 font-semibold uppercase">
          DENISBOT // J.A.R.V.I.S INTERFACE
        </span>
      </div>

      <div className="flex items-center gap-6 text-[11px] tracking-wide text-hud-cyan/70">
        <div className="flex items-center gap-2">
          <Thermometer className="h-3.5 w-3.5 text-hud-amber" />
          <span>
            {weather ? `${weather.tempC}°C` : '--°C'} / {weather?.condition ?? '--'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Activity className="h-3.5 w-3.5 text-hud-cyan" />
          <span>OPERATOR: DENIS</span>
        </div>
        <span>SYS: CachyOS</span>
        <span>UPTIME: {metrics.uptime}</span>
        <span className="inline-flex items-center gap-2 text-emerald-400">
          <span className="h-2 w-2 rounded-full bg-emerald-400 hud-glow" />
          STATUS: &gt; NOMINAL
        </span>
        <span className="text-hud-muted">{time} / {date}</span>
      </div>
    </header>
  )
}
