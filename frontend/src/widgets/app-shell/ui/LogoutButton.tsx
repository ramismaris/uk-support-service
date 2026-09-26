import { LogOut } from 'lucide-react'
import { isInMax } from '@/shared/lib/max-bridge'
import { useLogout } from '../model/use-logout'

// Quiet on purpose: signing out is rare and must not outweigh the user's name.
export function LogoutButton({ compact = false }: { compact?: boolean }) {
  const logout = useLogout()
  if (isInMax()) {
    return null
  }
  return (
    <button
      type="button"
      aria-label="Выйти"
      title="Выйти"
      disabled={logout.isPending}
      onClick={() => logout.mutate()}
      className={`flex items-center gap-2 rounded-lg text-sm text-fg-3 transition-colors hover:bg-hover hover:text-fg ${
        compact ? 'size-10 justify-center' : 'px-3 py-2'
      }`}
    >
      <LogOut size={18} strokeWidth={2} />
      {!compact && 'Выйти'}
    </button>
  )
}
