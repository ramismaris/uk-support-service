const FALLBACK_MESSAGE = 'Что-то пошло не так. Попробуйте ещё раз.'
const NETWORK_MESSAGE = 'Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.'
// No response at all: the server is down or the device is offline.
export const NETWORK_ERROR_STATUS = 0

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

const PYDANTIC_PREFIX = /^Value error, /
const CYRILLIC = /[а-яё]/i

// 422 from FastAPI lists pydantic errors. Our own validators speak Russian; pydantic's
// built-in ones ("Field required") are for developers, so those fall back to the generic text.
function validationMessage(detail: unknown[]): string | null {
  const first = detail[0]
  if (!first || typeof first !== 'object' || !('msg' in first) || typeof first.msg !== 'string') {
    return null
  }
  const message = first.msg.replace(PYDANTIC_PREFIX, '')
  return CYRILLIC.test(message) ? message : null
}

function messageFrom(body: unknown): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    if (typeof body.detail === 'string') {
      return body.detail
    }
    if (Array.isArray(body.detail)) {
      return validationMessage(body.detail) ?? FALLBACK_MESSAGE
    }
  }
  return FALLBACK_MESSAGE
}

interface FetchResult<T> {
  data?: T
  error?: unknown
  response: Response
}

export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>
  try {
    result = await request
  } catch (error) {
    // A cancelled request is not a failure to show.
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error
    }
    // fetch rejects only when no response came back ("Failed to fetch").
    throw new ApiError(NETWORK_ERROR_STATUS, NETWORK_MESSAGE)
  }
  const { data, error, response } = result
  if (!response.ok) {
    throw new ApiError(response.status, messageFrom(error))
  }
  return data as T
}
