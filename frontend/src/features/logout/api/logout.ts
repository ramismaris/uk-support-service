import { api, unwrap } from '@/shared/api'

export function logout() {
  return unwrap(api.POST('/api/v1/auth/logout'))
}
