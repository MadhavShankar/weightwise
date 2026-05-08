import { useEffect, useCallback } from 'react'
import { AppState } from 'react-native'
import { api } from '@/lib/api'
import { useTodayStore } from '@/stores/today'

export function useToday() {
  const setToday = useTodayStore((s) => s.setToday)

  const refresh = useCallback(async () => {
    try {
      const summary = await api.get<Parameters<typeof setToday>[0]>('/api/today/summary')
      setToday(summary)
    } catch {
      // silently fail — stale data is better than a crash
    }
  }, [setToday])

  useEffect(() => {
    refresh()
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') refresh()
    })

    // Reset at local midnight
    const now = new Date()
    const nextMidnight = new Date(now)
    nextMidnight.setDate(now.getDate() + 1)
    nextMidnight.setHours(0, 0, 0, 0)
    const msUntilMidnight = nextMidnight.getTime() - now.getTime()
    const timer = setTimeout(() => refresh(), msUntilMidnight)

    return () => {
      sub.remove()
      clearTimeout(timer)
    }
  }, [refresh])

  return { refresh }
}
