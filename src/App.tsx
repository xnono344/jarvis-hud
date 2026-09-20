import { JarvisProvider } from './store/JarvisProvider'
import TopHeader from './components/TopHeader'
import CenterHub from './components/CenterHub/CenterHub'
import GrowthPipeline from './components/LeftDeck/GrowthPipeline'
import SystemHealth from './components/LeftDeck/SystemHealth'
import TaskManager from './components/LeftDeck/TaskManager'
import CRMStats from './components/RightDeck/CRMStats'
import ActivityPulse from './components/RightDeck/ActivityPulse'
import AgentCommons from './components/RightDeck/AgentCommons'
import QuickNav from './components/BottomDeck/QuickNav'
import CommandConsole from './components/BottomDeck/CommandConsole'

export default function App() {
  return (
    <JarvisProvider>
      <div className="flex h-screen w-screen flex-col bg-hud-bg text-hud-cyan overflow-hidden">
        {/* Decorative grid overlay. MUST stay pointer-events-none: the old
            `.scanlines` class sets pointer-events:none and it used to sit on
            the root container, which inherited down and made every
            button/input on screen unclickable. */}
        <div aria-hidden className="scanlines pointer-events-none fixed inset-0 z-50" />
        <TopHeader />

        <div className="flex min-h-0 flex-1 gap-4 p-4">
          <div className="flex w-64 shrink-0 flex-col gap-3 overflow-y-auto">
            <GrowthPipeline />
            <SystemHealth />
            <TaskManager />
          </div>

          <div className="flex flex-1 items-center justify-center">
            <CenterHub />
          </div>

          <div className="flex w-64 shrink-0 flex-col gap-3 overflow-y-auto">
            <CRMStats />
            <ActivityPulse />
            <AgentCommons />
          </div>
        </div>

        <div className="shrink-0 border-t border-hud-border/60 bg-hud-panel/40 p-3 backdrop-blur-md">
          <QuickNav />
          <div className="mt-2">
            <CommandConsole />
          </div>
        </div>
      </div>
    </JarvisProvider>
  )
}
