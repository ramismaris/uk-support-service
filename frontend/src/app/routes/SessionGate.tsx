import { Button } from '@maxhub/max-ui'
import { useEffect } from 'react'
import { Navigate, Outlet } from 'react-router'
import { useMe, useSessionStore } from '@/entities/session'
import { useLoginByMax } from '@/features/auth-by-max'
import { routePaths } from '@/shared/config'
import { isInMax } from '@/shared/lib/max-bridge'
import { SplashScreen } from '@/shared/ui/splash-screen'
import { StatusScreen } from '@/shared/ui/status-screen'
import { resolveSessionState } from './session-state'

export function SessionGate() {
  const token = useSessionStore((state) => state.token)
  const me = useMe()
  const maxLogin = useLoginByMax()
  const { mutate: loginByMax, reset: resetMaxLogin } = maxLogin
  const inMax = isInMax()

  const shouldLoginByMax = inMax && token === null && !maxLogin.isPending && !maxLogin.isError
  useEffect(() => {
    if (shouldLoginByMax) {
      loginByMax()
    }
  }, [shouldLoginByMax, loginByMax])

  const state = resolveSessionState({
    token,
    inMax,
    me: { data: me.data, error: me.error },
    maxLogin: { error: maxLogin.error },
  })

  const retry = () => {
    if (token !== null) {
      void me.refetch()
    } else {
      // Clearing the error re-enables the effect above, which signs in again.
      resetMaxLogin()
    }
  }

  switch (state.kind) {
    case 'ready':
      return <Outlet />
    case 'unauthenticated':
      return <Navigate to={routePaths.login} replace />
    case 'loading':
      return <SplashScreen />
    case 'blocked':
      return (
        <StatusScreen
          title="Доступ ограничен"
          text="Ваш аккаунт заблокирован. Обратитесь в управляющую компанию."
        />
      )
    case 'error':
      return (
        <StatusScreen
          title="Не удалось войти"
          text={state.message}
          action={<Button onClick={retry}>Повторить</Button>}
        />
      )
  }
}
