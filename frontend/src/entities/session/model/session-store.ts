import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SessionState {
  token: string | null
  setToken: (token: string) => void
  clear: () => void
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      token: null,
      setToken: (token) => set({ token }),
      clear: () => set({ token: null }),
    }),
    { name: 'uk-session', partialize: (state) => ({ token: state.token }) },
  ),
)
