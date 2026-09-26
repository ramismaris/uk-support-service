import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { useMe } from '@/entities/session'
import type { User } from '@/entities/user'
import { routePaths } from '@/shared/config'

interface RequireRoleProps {
  allow: (user: User) => boolean
  children: ReactNode
}

export function RequireRole({ allow, children }: RequireRoleProps) {
  const { data: user } = useMe()
  if (!user) {
    return null
  }
  if (!allow(user)) {
    return <Navigate to={routePaths.home} replace />
  }
  return children
}
