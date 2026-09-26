import { api, unwrap } from '@/shared/api'

export function devLogin(maxUserId: number) {
  return unwrap(api.POST('/api/v1/auth/dev', { body: { max_user_id: maxUserId } }))
}
