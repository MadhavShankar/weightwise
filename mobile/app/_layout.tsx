import '../global.css'
import { useEffect } from 'react'
import { Stack } from 'expo-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/lib/api'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 2, staleTime: 30_000 } },
})

export default function RootLayout() {
  const setSession = useAuthStore((s) => s.setSession)
  const setInternalId = useAuthStore((s) => s.setInternalId)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      if (session) resolveInternalId()
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      if (session) resolveInternalId()
    })

    return () => subscription.unsubscribe()
  }, [])

  async function resolveInternalId() {
    try {
      const me = await api.get<{ internal_id: number | null }>('/api/auth/me')
      if (me.internal_id) setInternalId(me.internal_id)
    } catch {}
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Stack screenOptions={{ headerShown: false }} />
    </QueryClientProvider>
  )
}
