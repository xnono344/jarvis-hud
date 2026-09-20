import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useJarvis } from '../../store/JarvisContext'
import type { TaskItem } from '../../store/types'

const FILTERS = ['ALL', 'IN-PROGRESS', 'REVIEW', 'BLOCKED'] as const

export default function TaskManager() {
  const { tasks, toggleTask, addTask } = useJarvis()
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>('ALL')
  const [newTitle, setNewTitle] = useState('')
  const [newTag, setNewTag] = useState<TaskItem['tag']>('INTERNAL')

  const filtered =
    filter === 'ALL' ? tasks : tasks.filter((t) => t.tag.replace('-', ' ').toUpperCase() === filter)

  const handleAdd = () => {
    if (!newTitle.trim()) return
    addTask(newTitle, newTag)
    setNewTitle('')
  }

  return (
    <div className="hud-panel hud-chamfer p-3">
      <div className="flex items-center justify-between">
        <h3 className="text-[11px] tracking-widest text-hud-cyan/70">PROJECTS // TASKS</h3>
        <span className="text-[10px] text-hud-muted">{tasks.filter((t) => !t.completed).length} OPEN</span>
      </div>

      <div className="mt-2 flex gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-full border px-2 py-0.5 text-[10px] transition ${
              filter === f
                ? 'border-hud-cyan/60 bg-hud-cyan/10 text-hud-cyan'
                : 'border-hud-border/40 text-hud-muted hover:text-hud-cyan'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      <div className="mt-3 space-y-2">
        <AnimatePresence>
          {filtered.map((task) => (
            <motion.label
              key={task.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              className="flex items-center gap-2 text-[11px]"
            >
              <input
                type="checkbox"
                checked={task.completed}
                onChange={() => toggleTask(task.id)}
                className="accent-hud-cyan"
              />
              <span className={task.completed ? 'text-hud-muted line-through' : 'text-hud-cyan/80'}>{task.title}</span>
              <span
                className={`ml-auto rounded-full border px-1.5 py-0.5 text-[9px] ${
                  task.tag === 'CURRENT'
                    ? 'border-hud-cyan/40 text-hud-cyan'
                    : task.tag === 'IN-PROGRESS'
                      ? 'border-hud-amber/40 text-hud-amber'
                      : 'border-hud-border/40 text-hud-muted'
                }`}
              >
                {task.tag}
              </span>
            </motion.label>
          ))}
        </AnimatePresence>
      </div>

      <div className="mt-3 flex items-center gap-2 border-t border-hud-border/40 pt-2">
        <input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="+ Add task (e.g. Call about inventory)"
          className="w-full bg-transparent text-[11px] text-hud-cyan placeholder:text-hud-muted outline-none"
        />
        <select
          value={newTag}
          onChange={(e) => setNewTag(e.target.value as TaskItem['tag'])}
          className="bg-hud-panel border border-hud-border/40 rounded px-1 text-[10px] text-hud-cyan outline-none"
        >
          <option value="INTERNAL">INTERNAL</option>
          <option value="IN-PROGRESS">IN-PROGRESS</option>
          <option value="CURRENT">CURRENT</option>
          <option value="BLOCKED">BLOCKED</option>
        </select>
        <button onClick={handleAdd} className="text-[10px] text-hud-cyan hover:text-white">
          ADD
        </button>
      </div>
    </div>
  )
}
