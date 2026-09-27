import { Menu } from 'lucide-react'
import { useUnreadCount } from '@/entities/ticket'
import { useNavDrawer } from '../model/nav-drawer'

export function NavMenuButton() {
  const setOpen = useNavDrawer((state) => state.setOpen)
  const hasUnread = (useUnreadCount().data ?? 0) > 0
  return (
    <button
      type="button"
      aria-label={hasUnread ? 'Меню, есть непрочитанные' : 'Меню'}
      onClick={() => setOpen(true)}
      className="relative -ml-1 rounded-full p-1.5 hover:bg-hover lg:hidden"
    >
      <Menu size={22} strokeWidth={2} />
      {hasUnread && (
        <span className="absolute top-1 right-1 size-2.5 rounded-full bg-brand ring-2 ring-surface" />
      )}
    </button>
  )
}
