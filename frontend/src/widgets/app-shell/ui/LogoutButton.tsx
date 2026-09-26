import { Button } from '@maxhub/max-ui'
import { isInMax } from '@/shared/lib/max-bridge'
import { useLogout } from '../model/use-logout'

export function LogoutButton() {
  const logout = useLogout()
  if (isInMax()) {
    return null
  }
  return (
    <Button variant="ghost" size="small" loading={logout.isPending} onClick={() => logout.mutate()}>
      Выйти
    </Button>
  )
}
