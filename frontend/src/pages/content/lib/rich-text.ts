import type { JSONContent } from '@tiptap/react'
import { parseMaxMarkdown, type InlineNode } from '@/shared/lib/max-markdown'

// The editor shows formatting; the bot gets Max markdown. These two turn one into the other.

type MarkJSON = { type: string; attrs?: { href: string } }

const STYLE_MARK: Record<string, string> = {
  bold: 'bold',
  italic: 'italic',
  underline: 'underline',
  strike: 'strike',
  mark: 'highlight',
}

function inlineToText(nodes: InlineNode[], marks: MarkJSON[] = []): JSONContent[] {
  return nodes.flatMap((node): JSONContent[] => {
    if (node.type === 'text' || node.type === 'code') {
      const all = node.type === 'code' ? [...marks, { type: 'code' }] : marks
      return [{ type: 'text', text: node.text, ...(all.length > 0 ? { marks: all } : {}) }]
    }
    if (node.type === 'link') {
      return inlineToText(node.children, [...marks, { type: 'link', attrs: { href: node.href } }])
    }
    return inlineToText(node.children, [...marks, { type: STYLE_MARK[node.type]! }])
  })
}

function paragraph(children: InlineNode[]): JSONContent {
  const content = inlineToText(children)
  return content.length > 0 ? { type: 'paragraph', content } : { type: 'paragraph' }
}

export function markdownToDoc(markdown: string): JSONContent {
  return {
    type: 'doc',
    content: parseMaxMarkdown(markdown).map((block) => {
      if (block.type === 'heading') {
        return { type: 'heading', attrs: { level: 1 }, content: inlineToText(block.children) }
      }
      if (block.type === 'quote') {
        return { type: 'blockquote', content: [paragraph(block.children)] }
      }
      return paragraph(block.children)
    }),
  }
}

// Outer to inner: a link wraps styles, code sits innermost as it cannot hold markers.
const MARK_ORDER = ['link', 'bold', 'italic', 'underline', 'strike', 'highlight', 'code']
const MARKERS: Record<string, string> = {
  bold: '**',
  italic: '_',
  underline: '++',
  strike: '~~',
  highlight: '^^',
  code: '`',
}

const markKey = (mark: MarkJSON) => `${mark.type}:${mark.attrs?.href ?? ''}`

function sortMarks(marks: MarkJSON[]): MarkJSON[] {
  return marks
    .filter((mark) => MARK_ORDER.includes(mark.type))
    .sort((a, b) => MARK_ORDER.indexOf(a.type) - MARK_ORDER.indexOf(b.type))
}

const opener = (mark: MarkJSON) => (mark.type === 'link' ? '[' : MARKERS[mark.type]!)
const closer = (mark: MarkJSON) =>
  mark.type === 'link' ? `](${mark.attrs?.href ?? ''})` : MARKERS[mark.type]!

interface Segment {
  text: string
  marks: MarkJSON[]
}

function shared(marks: MarkJSON[], other: MarkJSON[] | undefined): MarkJSON[] {
  const keys = new Set((other ?? []).map(markKey))
  return marks.filter((mark) => keys.has(markKey(mark)))
}

// "**word **" does not render in Max: spaces at a mark's edge only keep the marks the
// neighbour shares, so the markers close before the space.
function segments(nodes: JSONContent[]): Segment[] {
  const texts = nodes.map((node) => ({
    text: node.text ?? '',
    marks: sortMarks((node.marks ?? []) as MarkJSON[]),
  }))
  return texts.flatMap((node, index) => {
    const core = node.text.trim()
    if (core === '') {
      const around = shared(shared(node.marks, texts[index - 1]?.marks), texts[index + 1]?.marks)
      return [{ text: node.text, marks: around }]
    }
    const lead = node.text.slice(0, node.text.length - node.text.trimStart().length)
    const trail = node.text.slice(node.text.trimEnd().length)
    return [
      { text: lead, marks: shared(node.marks, texts[index - 1]?.marks) },
      { text: core, marks: node.marks },
      { text: trail, marks: shared(node.marks, texts[index + 1]?.marks) },
    ].filter((segment) => segment.text !== '')
  })
}

function lineToMarkdown(nodes: JSONContent[]): string {
  let out = ''
  let open: MarkJSON[] = []
  for (const segment of segments(nodes)) {
    let common = 0
    while (
      common < open.length &&
      common < segment.marks.length &&
      markKey(open[common]!) === markKey(segment.marks[common]!)
    ) {
      common += 1
    }
    for (const mark of open.slice(common).reverse()) {
      out += closer(mark)
    }
    for (const mark of segment.marks.slice(common)) {
      out += opener(mark)
    }
    open = segment.marks
    out += segment.text
  }
  for (const mark of [...open].reverse()) {
    out += closer(mark)
  }
  return out
}

// A hard break (Shift+Enter) is a new line in Max too; markers never cross a line.
function inlineToMarkdown(content: JSONContent[] = []): string {
  const lines: JSONContent[][] = [[]]
  for (const node of content) {
    if (node.type === 'hardBreak') {
      lines.push([])
    } else if (node.type === 'text') {
      lines.at(-1)!.push(node)
    }
  }
  return lines.map(lineToMarkdown).join('\n')
}

export function docToMarkdown(doc: JSONContent): string {
  return (doc.content ?? [])
    .map((block) => {
      if (block.type === 'heading') {
        return `# ${inlineToMarkdown(block.content)}`
      }
      if (block.type === 'blockquote') {
        return (block.content ?? [])
          .map((child) => `> ${inlineToMarkdown(child.content)}`)
          .join('\n')
      }
      return inlineToMarkdown(block.content)
    })
    .join('\n')
}
