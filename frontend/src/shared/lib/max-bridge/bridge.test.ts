import { afterEach, describe, expect, it } from 'vitest'
import { getInitData, getStartParam, isInMax } from './bridge'

afterEach(() => {
  delete window.WebApp
})

describe('max bridge', () => {
  it('is a plain browser when the Max script is absent', () => {
    expect(isInMax()).toBe(false)
    expect(getInitData()).toBe('')
    expect(getStartParam()).toBeNull()
  })

  it('is a plain browser when initData is empty (script loaded outside Max)', () => {
    window.WebApp = { initData: '' }
    expect(isInMax()).toBe(false)
  })

  it('reads initData and start_param inside Max', () => {
    window.WebApp = { initData: 'user=1&hash=x', initDataUnsafe: { start_param: 'ticket_1042' } }
    expect(isInMax()).toBe(true)
    expect(getInitData()).toBe('user=1&hash=x')
    expect(getStartParam()).toBe('ticket_1042')
  })

  it('ignores a non-string or empty start_param', () => {
    window.WebApp = { initData: 'x', initDataUnsafe: { start_param: { value: 1 } } }
    expect(getStartParam()).toBeNull()
    window.WebApp = { initData: 'x', initDataUnsafe: { start_param: '' } }
    expect(getStartParam()).toBeNull()
  })
})
