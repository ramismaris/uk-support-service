// Letters only: company names come with quotes and dashes («Наш дом», ЖЭК-5).
export function brandInitials(name: string): string {
  return (name.match(/\p{L}+/gu) ?? [])
    .map((word) => word.charAt(0))
    .join('')
    .slice(0, 2)
    .toUpperCase()
}
