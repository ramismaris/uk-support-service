export interface CategoryTitle {
  emoji: string | null
  name: string
}

// Titles come from the bot's menu with the emoji first ("🔧 Сантехника"). \p{Extended_Pictographic}
// leaves digits out, and the tail takes variation selectors and joiners so the emoji stays whole.
const LEADING_EMOJI = /^(\p{Extended_Pictographic}[️‍\p{Extended_Pictographic}]*)\s*(.*)$/su

export function splitCategoryTitle(title: string): CategoryTitle {
  const match = LEADING_EMOJI.exec(title)
  return match ? { emoji: match[1], name: match[2] } : { emoji: null, name: title }
}
