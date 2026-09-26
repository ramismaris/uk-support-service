import { ticketPath } from '@/shared/config'
import { getStartParam } from '@/shared/lib/max-bridge'

const TICKET_PARAM = /^ticket_([1-9]\d*)$/

export function ticketPathFromStartParam(param: string | null): string | null {
  const match = param ? TICKET_PARAM.exec(param) : null
  if (!match) {
    return null
  }
  const id = Number(match[1])
  return Number.isSafeInteger(id) ? ticketPath(id) : null
}

// The start param belongs to this page load only: after the first redirect "/" goes home again.
let startPath = ticketPathFromStartParam(getStartParam())

export function takeStartPath(): string | null {
  return startPath
}

export function forgetStartPath(): void {
  startPath = null
}
