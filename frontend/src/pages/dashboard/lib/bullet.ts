export interface Bullet {
  // Bar length: the actual value, 0..1 of the scale.
  fill: number
  // Position of the norm tick, 0..1 of the scale.
  mark: number
  over: boolean
}

// A value against its norm on one scale, reaching a quarter past the larger of the two.
export function bullet(value: number, norm: number): Bullet {
  const scale = Math.max(value, norm) * 1.25
  return { fill: value / scale, mark: norm / scale, over: value > norm }
}
