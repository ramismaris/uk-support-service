import { useEffect } from 'react'
import { Navigate } from 'react-router'
import { useMe } from '@/entities/session'
import { isStaff } from '@/entities/user'
import { forgetStartPath, takeStartPath } from './deep-link'
import { homePathFor } from './home-path'

export function RoleRedirect() {
  const { data: user } = useMe()

  // Forget after commit, not during render: StrictMode renders twice.
  useEffect(() => forgetStartPath(), [])

  if (!user) {
    return null
  }
  const startPath = isStaff(user) ? takeStartPath() : null
  return <Navigate to={startPath ?? homePathFor(user)} replace />
}
