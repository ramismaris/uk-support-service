import { create } from 'zustand'

interface SocketStatusState {
  online: boolean
  setOnline: (online: boolean) => void
}

// Optimistic: the indicator appears only after a real drop.
export const useSocketStatus = create<SocketStatusState>()((set) => ({
  online: true,
  setOnline: (online) => set({ online }),
}))
