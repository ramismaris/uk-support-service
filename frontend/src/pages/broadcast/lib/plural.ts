export function plural(n: number, one: string, few: string, many: string): string {
  const lastTwo = n % 100
  const last = n % 10
  if (lastTwo >= 11 && lastTwo <= 14) {
    return many
  }
  if (last === 1) {
    return one
  }
  return last >= 2 && last <= 4 ? few : many
}
