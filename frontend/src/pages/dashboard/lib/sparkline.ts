const round = (value: number) => Math.round(value * 100) / 100

export function sparklinePath(values: number[], width: number, height: number): string {
  if (values.length === 0) {
    return ''
  }
  const points = values.length === 1 ? [values[0], values[0]] : values
  const max = Math.max(...points)
  const step = width / (points.length - 1)
  return points
    .map((value, index) => {
      const x = round(index * step)
      const y = round(max > 0 ? height - (value / max) * height : height)
      return `${index === 0 ? 'M' : 'L'}${x},${y}`
    })
    .join(' ')
}
