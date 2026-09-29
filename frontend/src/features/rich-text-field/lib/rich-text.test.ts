import { describe, expect, it } from 'vitest'
import { docToMarkdown, markdownToDoc } from './rich-text'

const roundTrip = (markdown: string) => docToMarkdown(markdownToDoc(markdown))

describe('markdownToDoc', () => {
  it('makes a paragraph per line and keeps empty lines', () => {
    expect(markdownToDoc('Привет\n\nмир')).toEqual({
      type: 'doc',
      content: [
        { type: 'paragraph', content: [{ type: 'text', text: 'Привет' }] },
        { type: 'paragraph' },
        { type: 'paragraph', content: [{ type: 'text', text: 'мир' }] },
      ],
    })
  })

  it('turns markers into marks, nested ones too', () => {
    expect(markdownToDoc('**жирный _и курсив_**').content).toEqual([
      {
        type: 'paragraph',
        content: [
          { type: 'text', text: 'жирный ', marks: [{ type: 'bold' }] },
          { type: 'text', text: 'и курсив', marks: [{ type: 'bold' }, { type: 'italic' }] },
        ],
      },
    ])
  })

  it('reads links, headings and quotes', () => {
    expect(markdownToDoc('# Контакты\n> важно\n[сайт](https://uk.example)').content).toEqual([
      { type: 'heading', attrs: { level: 1 }, content: [{ type: 'text', text: 'Контакты' }] },
      {
        type: 'blockquote',
        content: [{ type: 'paragraph', content: [{ type: 'text', text: 'важно' }] }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            text: 'сайт',
            marks: [{ type: 'link', attrs: { href: 'https://uk.example' } }],
          },
        ],
      },
    ])
  })
})

describe('docToMarkdown', () => {
  it.each([
    'Просто текст',
    '**жирный** и _курсив_',
    '++подчёркнутый++ ~~зачёркнутый~~ ^^маркер^^ `код`',
    '**жирный _и курсив_**',
    '# Контакты\n> важно\n\n[сайт](https://uk.example)',
    '👋 Здравствуйте!\n\nВыберите раздел 👇',
  ])('gives back the same markdown: %s', (markdown) => {
    expect(roundTrip(markdown)).toBe(markdown)
  })

  it('keeps spaces at the edges of a mark outside the markers', () => {
    expect(
      docToMarkdown({
        type: 'doc',
        content: [
          {
            type: 'paragraph',
            content: [
              { type: 'text', text: 'Вход ' },
              { type: 'text', text: 'со двора ', marks: [{ type: 'bold' }] },
              { type: 'text', text: 'открыт' },
            ],
          },
        ],
      }),
    ).toBe('Вход **со двора** открыт')
  })

  it('does not close and reopen a mark shared by neighbouring pieces', () => {
    expect(
      docToMarkdown({
        type: 'doc',
        content: [
          {
            type: 'paragraph',
            content: [
              { type: 'text', text: 'один ', marks: [{ type: 'bold' }] },
              { type: 'text', text: 'два', marks: [{ type: 'bold' }, { type: 'italic' }] },
            ],
          },
        ],
      }),
    ).toBe('**один _два_**')
  })

  it('turns a line break inside a paragraph into a new line', () => {
    expect(
      docToMarkdown({
        type: 'doc',
        content: [
          {
            type: 'paragraph',
            content: [
              { type: 'text', text: 'а' },
              { type: 'hardBreak' },
              { type: 'text', text: 'б' },
            ],
          },
        ],
      }),
    ).toBe('а\nб')
  })
})
