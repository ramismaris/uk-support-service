import { describe, expect, it } from 'vitest'
import { parseInline, parseMaxMarkdown } from './parse'

describe('parseInline', () => {
  it('keeps plain text as is', () => {
    expect(parseInline('Мастер придёт завтра')).toEqual([
      { type: 'text', text: 'Мастер придёт завтра' },
    ])
  })

  it.each([
    ['**жирный**', 'bold'],
    ['__жирный__', 'bold'],
    ['*курсив*', 'italic'],
    ['_курсив_', 'italic'],
    ['~~зачёркнутый~~', 'strike'],
    ['++подчёркнутый++', 'underline'],
    ['^^маркер^^', 'mark'],
  ] as const)('reads %s as %s', (source, type) => {
    const [node] = parseInline(source)
    expect(node?.type).toBe(type)
  })

  it('reads inline code without formatting inside', () => {
    expect(parseInline('`**x**`')).toEqual([{ type: 'code', text: '**x**' }])
  })

  it('nests styles', () => {
    expect(parseInline('**жирный _и курсив_**')).toEqual([
      {
        type: 'bold',
        children: [
          { type: 'text', text: 'жирный ' },
          { type: 'italic', children: [{ type: 'text', text: 'и курсив' }] },
        ],
      },
    ])
  })

  it('reads links', () => {
    expect(parseInline('[сайт](https://uk.example)')).toEqual([
      { type: 'link', href: 'https://uk.example', children: [{ type: 'text', text: 'сайт' }] },
    ])
  })

  it('leaves links with unsafe schemes as text', () => {
    expect(parseInline('[x](javascript:alert(1))')).toEqual([
      { type: 'text', text: '[x](javascript:alert(1))' },
    ])
  })

  it('leaves unclosed and empty markers as text', () => {
    expect(parseInline('5 * 3 = 15')).toEqual([{ type: 'text', text: '5 * 3 = 15' }])
    expect(parseInline('** **x')).toEqual([{ type: 'text', text: '** **x' }])
    expect(parseInline('a**b')).toEqual([{ type: 'text', text: 'a**b' }])
  })
})

describe('parseMaxMarkdown', () => {
  it('splits lines and reads headings and quotes', () => {
    expect(parseMaxMarkdown('# Заголовок\n> цитата\nтекст')).toEqual([
      { type: 'heading', children: [{ type: 'text', text: 'Заголовок' }] },
      { type: 'quote', children: [{ type: 'text', text: 'цитата' }] },
      { type: 'line', children: [{ type: 'text', text: 'текст' }] },
    ])
  })

  it('keeps empty lines', () => {
    expect(parseMaxMarkdown('a\n\nb')).toHaveLength(3)
  })
})
