import { draftKey } from '@/shared/lib/drafts'
import { useMe } from '../api/me'

// A form's draft key for the signed-in user; null until the user is known.
export function useDraftKey(form: string): string | null {
  const { data: user } = useMe()
  return user ? draftKey(user.id, form) : null
}
