import type {} from './types'

export function isInMax(): boolean {
  return Boolean(window.WebApp?.initData)
}

export function getInitData(): string {
  return window.WebApp?.initData ?? ''
}

export function getStartParam(): string | null {
  const value = window.WebApp?.initDataUnsafe?.start_param
  return typeof value === 'string' && value !== '' ? value : null
}
