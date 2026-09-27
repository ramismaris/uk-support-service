import { QueryClient } from '@tanstack/react-query'
import { ApiError, NETWORK_ERROR_STATUS } from './errors'

export function shouldRetry(failureCount: number, error: unknown): boolean {
  // Client errors will not change on a retry; a lost connection and server errors may.
  if (error instanceof ApiError && error.status !== NETWORK_ERROR_STATUS && error.status < 500) {
    return false
  }
  return failureCount < 2
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: shouldRetry, staleTime: 30_000 },
    mutations: { retry: false },
  },
})
