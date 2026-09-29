export interface Bullet {
  fill: number
  mark: number
  over: boolean
}

export function bullet(value: number, norm: number): Bullet {
  const scale = Math.max(value, norm) * 1.25
  return { fill: value / scale, mark: norm / scale, over: value > norm }
}
