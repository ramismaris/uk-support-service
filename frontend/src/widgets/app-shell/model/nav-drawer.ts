import { create } from 'zustand'

interface NavDrawerState {
  open: boolean
  setOpen: (open: boolean) => void
}

// Phone navigation: the drawer lives in the shell, the button in each page's header.
export const useNavDrawer = create<NavDrawerState>()((set) => ({
  open: false,
  setOpen: (open) => set({ open }),
}))
