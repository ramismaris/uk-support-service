export function moveId(ids: number[], id: number, delta: -1 | 1): number[] {
  const from = ids.indexOf(id)
  const to = from + delta
  if (from === -1 || to < 0 || to >= ids.length) {
    return [...ids]
  }
  const next = [...ids]
  next[from] = next[to]
  next[to] = id
  return next
}
