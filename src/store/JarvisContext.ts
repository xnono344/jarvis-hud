import { createContext, useContext } from 'react'
import type { JarvisState } from './types'

export const JarvisContext = createContext<JarvisState | null>(null)

export const useJarvis = () => {
  const ctx = useContext(JarvisContext)
  if (!ctx) throw new Error('useJarvis must be used within JarvisProvider')
  return ctx
}
