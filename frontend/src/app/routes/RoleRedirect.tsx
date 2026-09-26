import { Navigate } from 'react-router'
import { useMe } from '@/entities/session'
import { homePathFor } from './home-path'

export function RoleRedirect() {
  const { data: user } = useMe()
  return user ? <Navigate to={homePathFor(user)} replace /> : null
}
