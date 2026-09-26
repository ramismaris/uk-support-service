import { api, unwrap } from '@/shared/api'

export function loginByMax(initData: string) {
  return unwrap(api.POST('/api/v1/auth/max', { body: { init_data: initData } }))
}
