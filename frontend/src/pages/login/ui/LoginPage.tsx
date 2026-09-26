import { Typography } from '@maxhub/max-ui'
import { Navigate } from 'react-router'
import { useSessionStore } from '@/entities/session'
import { DevLoginForm } from '@/features/auth-dev'
import { isDevAuthEnabled, routePaths } from '@/shared/config'
import { isInMax } from '@/shared/lib/max-bridge'
import { PageTransition } from '@/shared/ui/page-transition'

export function LoginPage() {
  const token = useSessionStore((state) => state.token)
  // Inside Max sign-in is automatic; a signed-in user has nothing to do here.
  if (isInMax() || token !== null) {
    return <Navigate to={routePaths.home} replace />
  }

  return (
    <div className="flex min-h-dvh items-center justify-center p-4">
      <PageTransition className="flex w-full max-w-sm flex-col gap-6">
        <Typography.Title>Вход в панель УК</Typography.Title>
        {isDevAuthEnabled ? (
          <DevLoginForm />
        ) : (
          <p className="text-neutral-500 dark:text-neutral-400">
            Напишите боту команду /panel — он пришлёт ссылку для входа.
          </p>
        )}
      </PageTransition>
    </div>
  )
}
