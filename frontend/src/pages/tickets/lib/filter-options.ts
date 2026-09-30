import type { TicketFilters } from '@/entities/ticket'

export interface SelectOption {
  value: number | null
  label: string
}

// A chosen id can be missing from the list (a link to a disabled house): it still has to show.
export function selectOptions(
  items: { id: number; label: string }[],
  selected: number | null,
  allLabel: string,
  missingLabel: (id: number) => string,
): SelectOption[] {
  const options: SelectOption[] = [
    { value: null, label: allLabel },
    ...items.map((item) => ({ value: item.id, label: item.label })),
  ]
  if (selected !== null && !items.some((item) => item.id === selected)) {
    options.push({ value: selected, label: missingLabel(selected) })
  }
  return options
}

export function hasActiveFilters(filters: TicketFilters): boolean {
  return (
    filters.status !== null ||
    filters.mine ||
    filters.buildingId !== null ||
    filters.categoryId !== null
  )
}
