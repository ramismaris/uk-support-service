import { Menu } from 'lucide-react'
import { useNavDrawer } from '../model/nav-drawer'

export function NavMenuButton() {
  const setOpen = useNavDrawer((state) => state.setOpen)
  return (
    <button
      type="button"
      aria-label="Меню"
      onClick={() => setOpen(true)}
      className="-ml-1 rounded-full p-1.5 hover:bg-neutral-100 lg:hidden dark:hover:bg-neutral-800"
    >
      <Menu size={22} strokeWidth={2} />
    </button>
  )
}
