const HEX = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i

// #RRGGBB → channels in 0..1, or null for anything else.
export function parseHexColor(value: string): [number, number, number] | null {
  const match = HEX.exec(value)
  if (!match) {
    return null
  }
  return [parseInt(match[1], 16) / 255, parseInt(match[2], 16) / 255, parseInt(match[3], 16) / 255]
}
