export interface CategoryTitle {
  emoji: string | null
  name: string
}

// The leading emoji with its variation selectors and joiners.
const LEADING_EMOJI =
  /^(\p{Extended_Pictographic}[\uFE0F\u200D\p{Extended_Pictographic}]*)\s*(.*)$/su

export function splitCategoryTitle(title: string): CategoryTitle {
  const match = LEADING_EMOJI.exec(title)
  return match ? { emoji: match[1], name: match[2] } : { emoji: null, name: title }
}
