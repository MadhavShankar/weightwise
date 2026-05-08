import { create } from 'zustand'
import type { Session } from '@supabase/supabase-js'

interface AuthStore {
  session: Session | null
  internalId: number | null
  setSession: (s: Session | null) => void
  setInternalId: (id: number) => void
  signOut: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  session: null,
  internalId: null,
  setSession: (session) => set({ session }),
  setInternalId: (internalId) => set({ internalId }),
  signOut: () => set({ session: null, internalId: null }),
}))
