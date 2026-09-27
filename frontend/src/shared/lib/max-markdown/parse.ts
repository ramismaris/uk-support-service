// Max bot markdown, as the resident sees it: https://dev.max.ru/docs-api (text formatting).

export type StyleType = 'bold' | 'italic' | 'strike' | 'underline' | 'mark'

export type InlineNode =
  | { type: 'text'; text: string }
  | { type: 'code'; text: string }
  | { type: StyleType; children: InlineNode[] }
  | { type: 'link'; href: string; children: InlineNode[] }

export interface BlockNode {
  type: 'line' | 'heading' | 'quote'
  children: InlineNode[]
}

// Longer markers first, so "**" is not read as two "*".
const MARKERS: [string, StyleType][] = [
  ['**', 'bold'],
  ['__', 'bold'],
  ['~~', 'strike'],
  ['++', 'underline'],
  ['^^', 'mark'],
  ['*', 'italic'],
  ['_', 'italic'],
]

const SAFE_LINK = /^(https?:\/\/|mailto:|tel:|max:\/\/)/i
const LINK = /^\[([^\]\n]+)\]\(([^)\s]+)\)/

function pushText(nodes: InlineNode[], text: string) {
  const last = nodes.at(-1)
  if (last?.type === 'text') {
    last.text += text
  } else {
    nodes.push({ type: 'text', text })
  }
}

export function parseInline(source: string): InlineNode[] {
  const nodes: InlineNode[] = []
  let i = 0
  outer: while (i < source.length) {
    const rest = source.slice(i)

    const link = LINK.exec(rest)
    if (link && SAFE_LINK.test(link[2]!)) {
      nodes.push({ type: 'link', href: link[2]!, children: parseInline(link[1]!) })
      i += link[0].length
      continue
    }

    if (rest.startsWith('`')) {
      const close = source.indexOf('`', i + 1)
      if (close > i + 1) {
        nodes.push({ type: 'code', text: source.slice(i + 1, close) })
        i = close + 1
        continue
      }
    }

    for (const [marker, type] of MARKERS) {
      if (!rest.startsWith(marker)) {
        continue
      }
      const start = i + marker.length
      const close = source.indexOf(marker, start)
      const inner = close === -1 ? '' : source.slice(start, close)
      // "5 * 3" or "** **": a marker needs text right after it and right before its pair.
      if (inner.trim() !== '' && inner === inner.trim()) {
        nodes.push({ type, children: parseInline(inner) })
        i = close + marker.length
        continue outer
      }
    }

    pushText(nodes, source[i]!)
    i += 1
  }
  return nodes
}

export function parseMaxMarkdown(source: string): BlockNode[] {
  return source.split('\n').map((line) => {
    if (line.startsWith('# ')) {
      return { type: 'heading', children: parseInline(line.slice(2)) }
    }
    if (line.startsWith('> ')) {
      return { type: 'quote', children: parseInline(line.slice(2)) }
    }
    return { type: 'line', children: parseInline(line) }
  })
}
