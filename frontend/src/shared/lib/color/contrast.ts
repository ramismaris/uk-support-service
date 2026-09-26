import { parseHexColor } from './hex'

// WCAG minimum for large text and UI parts; white labels sit on the brand colour.
export const LOW_CONTRAST = 3

function linear(channel: number): number {
  return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
}

export function contrastWithWhite(hex: string): number {
  const rgb = parseHexColor(hex)
  if (!rgb) {
    return 1
  }
  const [r, g, b] = rgb.map(linear)
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
  return 1.05 / (luminance + 0.05)
}
