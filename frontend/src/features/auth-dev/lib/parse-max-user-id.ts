export function parseMaxUserId(input: string): number | null {
  const value = input.trim()
  if (!/^\d+$/.test(value)) {
    return null
  }
  const id = Number(value)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}
