const FALLBACK_MESSAGE = 'Что-то пошло не так. Попробуйте ещё раз.'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function isApiError(error: unknown, status?: number): error is ApiError {
  return error instanceof ApiError && (status === undefined || error.status === status)
}

function messageFrom(body: unknown): string {
  if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
    return body.detail
  }
  return FALLBACK_MESSAGE
}

interface FetchResult<T> {
  data?: T
  error?: unknown
  response: Response
}

export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  const { data, error, response } = await request
  if (!response.ok) {
    throw new ApiError(response.status, messageFrom(error))
  }
  return data as T
}
