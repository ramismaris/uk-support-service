import { Typography } from '@maxhub/max-ui'
import { Navigate } from 'react-router'
import { useSessionStore } from '@/entities/session'
import { readCachedTheme } from '@/entities/theme'
import { isDevAuthEnabled, routePaths } from '@/shared/config'
import { isInMax } from '@/shared/lib/max-bridge'
import { PageTransition } from '@/shared/ui/page-transition'
import { DevLoginForm } from './DevLoginForm'

export function LoginPage() {
  const token = useSessionStore((state) => state.token)
  // Inside Max sign-in is automatic; a signed-in user has nothing to do here.
  if (isInMax() || token !== null) {
    return <Navigate to={routePaths.home} replace />
  }

  return (
    <div className="flex min-h-dvh items-center justify-center p-4">
      <PageTransition className="flex w-full max-w-sm flex-col gap-6">
        <div className="flex flex-col gap-1">
          <Typography.Title>{readCachedTheme().companyName}</Typography.Title>
          <p className="text-sm text-fg-2">Вход в панель сотрудника</p>
        </div>
        {isDevAuthEnabled ? (
          <DevLoginForm />
        ) : (
          <p className="text-fg-2">Напишите боту команду /panel — он пришлёт ссылку для входа.</p>
        )}
      </PageTransition>
    </div>
  )
}
