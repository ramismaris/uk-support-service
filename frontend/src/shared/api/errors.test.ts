import { describe, expect, it } from 'vitest'
import { ApiError, isApiError, unwrap } from './errors'

const response = (status: number) => new Response(null, { status })

describe('unwrap', () => {
  it('returns data for a successful response', async () => {
    const data = { id: 1 }
    await expect(unwrap(Promise.resolve({ data, response: response(200) }))).resolves.toBe(data)
  })

  it('returns undefined for 204', async () => {
    await expect(unwrap(Promise.resolve({ response: response(204) }))).resolves.toBeUndefined()
  })

  it('throws ApiError with backend detail message', async () => {
    const request = Promise.resolve({
      error: { detail: 'Пользователь не найден' },
      response: response(404),
    })
    await expect(unwrap(request)).rejects.toEqual(new ApiError(404, 'Пользователь не найден'))
  })

  it('falls back to a generic message when validation messages are not for people', async () => {
    const request = Promise.resolve({
      error: { detail: [{ msg: 'Field required' }] },
      response: response(422),
    })
    const error = await unwrap(request).catch((e: unknown) => e)
    expect(isApiError(error, 422)).toBe(true)
    expect((error as ApiError).message).toBe('Что-то пошло не так. Попробуйте ещё раз.')
  })

  it('shows the first Russian validation message, without the pydantic prefix', async () => {
    const request = Promise.resolve({
      error: { detail: [{ msg: 'Value error, Телефон указан неверно' }, { msg: 'Другое' }] },
      response: response(422),
    })
    await expect(unwrap(request)).rejects.toEqual(new ApiError(422, 'Телефон указан неверно'))
  })

  it('turns a network failure into a readable error', async () => {
    const error = await unwrap(Promise.reject(new TypeError('Failed to fetch'))).catch(
      (e: unknown) => e,
    )
    expect(isApiError(error, 0)).toBe(true)
    expect((error as ApiError).message).toBe(
      'Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.',
    )
  })

  it('leaves a cancelled request as is', async () => {
    const abort = new DOMException('aborted', 'AbortError')
    await expect(unwrap(Promise.reject(abort))).rejects.toBe(abort)
  })
})

describe('isApiError', () => {
  it('matches status when given', () => {
    const error = new ApiError(403, 'no')
    expect(isApiError(error)).toBe(true)
    expect(isApiError(error, 403)).toBe(true)
    expect(isApiError(error, 401)).toBe(false)
    expect(isApiError(new Error('x'))).toBe(false)
  })
})
