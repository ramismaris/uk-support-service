import { parseHexColor } from './hex'

function withAlpha(rgb: number[], color: number[]): number[] {
  return [...rgb, ...color.slice(3, 4)]
}

// Paints every stroke and fill of a Lottie animation, static or animated, keeping alpha.
export function recolorLottie(animation: unknown, hex: string): unknown {
  const rgb = parseHexColor(hex)
  if (!rgb) {
    return animation
  }
  const copy: unknown = structuredClone(animation)

  const paint = (node: unknown): void => {
    if (Array.isArray(node)) {
      node.forEach(paint)
      return
    }
    if (!node || typeof node !== 'object') {
      return
    }
    const record = node as Record<string, unknown>
    if ((record.ty === 'st' || record.ty === 'fl') && record.c && typeof record.c === 'object') {
      const color = record.c as { k: unknown }
      if (Array.isArray(color.k) && color.k.every((value) => typeof value === 'number')) {
        color.k = withAlpha(rgb, color.k as number[])
      } else if (Array.isArray(color.k)) {
        for (const frame of color.k as Record<string, unknown>[]) {
          for (const key of ['s', 'e']) {
            if (Array.isArray(frame[key])) {
              frame[key] = withAlpha(rgb, frame[key] as number[])
            }
          }
        }
      }
    }
    Object.values(record).forEach(paint)
  }

  paint(copy)
  return copy
}
