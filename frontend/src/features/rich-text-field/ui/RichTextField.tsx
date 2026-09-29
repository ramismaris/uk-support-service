import bold from '@material-symbols/svg-400/rounded/format_bold.svg?url'
import heading from '@material-symbols/svg-400/rounded/format_h1.svg?url'
import italic from '@material-symbols/svg-400/rounded/format_italic.svg?url'
import quote from '@material-symbols/svg-400/rounded/format_quote.svg?url'
import strike from '@material-symbols/svg-400/rounded/format_strikethrough.svg?url'
import underline from '@material-symbols/svg-400/rounded/format_underlined.svg?url'
import code from '@material-symbols/svg-400/rounded/code.svg?url'
import highlighter from '@material-symbols/svg-400/rounded/ink_highlighter.svg?url'
import link from '@material-symbols/svg-400/rounded/link.svg?url'
import Highlight from '@tiptap/extension-highlight'
import { EditorContent, useEditor, useEditorState, type Editor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { useId, useState } from 'react'
import { docToMarkdown, markdownToDoc } from '../lib/rich-text'

// Max's formatting only: no lists or code blocks, the bot could not show them.
const SAFE_LINK = /^(https?:\/\/|mailto:|tel:|max:\/\/)/i

const extensions = [
  StarterKit.configure({
    heading: { levels: [1] },
    bulletList: false,
    orderedList: false,
    listItem: false,
    listKeymap: false,
    codeBlock: false,
    horizontalRule: false,
    // An always-present empty last line would add a stray line break to the bot text.
    trailingNode: false,
    link: {
      openOnClick: false,
      defaultProtocol: 'https',
      isAllowedUri: (url) => SAFE_LINK.test(url),
    },
  }),
  Highlight,
]

// Material Symbols as a mask, so the icon takes the text colour of the button.
function Symbol({ src }: { src: string }) {
  return (
    <span
      aria-hidden
      className="size-5 bg-current"
      style={{ mask: `url("${src}") center / contain no-repeat` }}
    />
  )
}

interface Tool {
  label: string
  icon: string
  shortcut?: string
  isActive: (editor: Editor) => boolean
  run: (editor: Editor) => void
}

const TOOLS: Tool[][] = [
  [
    {
      label: 'Жирный',
      icon: bold,
      shortcut: 'Ctrl+B',
      isActive: (e) => e.isActive('bold'),
      run: (e) => e.chain().focus().toggleBold().run(),
    },
    {
      label: 'Курсив',
      icon: italic,
      shortcut: 'Ctrl+I',
      isActive: (e) => e.isActive('italic'),
      run: (e) => e.chain().focus().toggleItalic().run(),
    },
    {
      label: 'Подчёркнутый',
      icon: underline,
      shortcut: 'Ctrl+U',
      isActive: (e) => e.isActive('underline'),
      run: (e) => e.chain().focus().toggleUnderline().run(),
    },
    {
      label: 'Зачёркнутый',
      icon: strike,
      isActive: (e) => e.isActive('strike'),
      run: (e) => e.chain().focus().toggleStrike().run(),
    },
    {
      label: 'Выделение',
      icon: highlighter,
      isActive: (e) => e.isActive('highlight'),
      run: (e) => e.chain().focus().toggleHighlight().run(),
    },
    {
      label: 'Моноширинный',
      icon: code,
      isActive: (e) => e.isActive('code'),
      run: (e) => e.chain().focus().toggleCode().run(),
    },
  ],
  [
    {
      label: 'Заголовок',
      icon: heading,
      isActive: (e) => e.isActive('heading'),
      run: (e) => e.chain().focus().toggleHeading({ level: 1 }).run(),
    },
    {
      label: 'Цитата',
      icon: quote,
      isActive: (e) => e.isActive('blockquote'),
      run: (e) => e.chain().focus().toggleBlockquote().run(),
    },
  ],
]

const toolButton =
  'flex size-8 items-center justify-center rounded-lg transition-colors disabled:opacity-40'

function toolClass(active: boolean) {
  return `${toolButton} ${active ? 'bg-brand/15 text-brand' : 'text-fg-2 hover:bg-press hover:text-fg'}`
}

function LinkForm({ editor, onDone }: { editor: Editor; onDone: () => void }) {
  const [href, setHref] = useState('https://')
  const valid = SAFE_LINK.test(href) && href.length > 'https://'.length

  const submit = () => {
    if (!valid) {
      return
    }
    const chain = editor.chain().focus()
    // Nothing selected: the address itself becomes the link text.
    if (editor.state.selection.empty) {
      chain
        .insertContent({ type: 'text', text: href, marks: [{ type: 'link', attrs: { href } }] })
        .run()
    } else {
      chain.extendMarkRange('link').setLink({ href }).run()
    }
    onDone()
  }

  return (
    // Not a <form>: the field already sits inside the section form, and Enter must not save it.
    <div className="flex items-center gap-2 border-t border-line px-2 py-1.5">
      <input
        value={href}
        autoFocus
        aria-label="Адрес ссылки"
        onChange={(event) => setHref(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') {
            event.preventDefault()
            submit()
          } else if (event.key === 'Escape') {
            event.preventDefault()
            onDone()
            editor.commands.focus()
          }
        }}
        className="min-w-0 flex-1 bg-transparent px-1 py-1 text-sm outline-none"
      />
      <button
        type="button"
        disabled={!valid}
        onClick={submit}
        className="rounded-lg px-2 py-1 text-sm font-medium text-brand hover:bg-press disabled:opacity-40"
      >
        Готово
      </button>
    </div>
  )
}

interface RichTextFieldProps {
  label: string
  value: string
  limit: number
  error?: string
  onChange: (markdown: string) => void
}

// Looks like the message the resident gets; stores Max markdown.
export function RichTextField({ label, value, limit, error, onChange }: RichTextFieldProps) {
  const labelId = useId()
  const [linkOpen, setLinkOpen] = useState(false)
  const editor = useEditor({
    extensions,
    // The form remounts the field after a save, so the initial value is enough.
    content: markdownToDoc(value),
    editorProps: {
      attributes: {
        role: 'textbox',
        'aria-multiline': 'true',
        'aria-labelledby': labelId,
        class:
          'min-h-36 px-3 pt-1 pb-2.5 text-[15px] leading-5 outline-none [&_a]:text-brand [&_a]:underline [&_blockquote]:border-l [&_blockquote]:border-fg-3 [&_blockquote]:pl-2 [&_code]:rounded [&_code]:bg-press [&_code]:px-1 [&_code]:font-mono [&_code]:text-[0.9em] [&_h1]:text-lg [&_h1]:font-semibold [&_mark]:rounded-sm [&_mark]:bg-attention/30 [&_mark]:px-0.5 [&_mark]:text-inherit',
      },
    },
    onUpdate: ({ editor }) => onChange(docToMarkdown(editor.getJSON())),
  })

  const active = useEditorState({
    editor,
    selector: ({ editor }) => ({
      tools: Object.fromEntries(TOOLS.flat().map((tool) => [tool.label, tool.isActive(editor)])),
      link: editor.isActive('link'),
    }),
  })

  const toggleLink = () => {
    if (active.link) {
      editor.chain().focus().extendMarkRange('link').unsetLink().run()
    } else {
      setLinkOpen(!linkOpen)
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <span className="flex items-baseline justify-between gap-2 text-sm">
        <span id={labelId} className="font-medium">
          {label}
        </span>
        <span className="text-xs text-fg-3">
          {value.length}/{limit}
        </span>
      </span>
      <div className="flex flex-col overflow-hidden rounded-xl bg-fill focus-within:ring-2 focus-within:ring-brand/40">
        <div
          role="toolbar"
          aria-label="Форматирование"
          className="flex flex-wrap items-center gap-0.5 p-1"
        >
          {TOOLS.map((group, groupIndex) => (
            <div key={groupIndex} className="flex items-center gap-0.5">
              {groupIndex > 0 && <span className="mx-1 h-5 w-px bg-line" />}
              {group.map((tool) => {
                const isActive = active.tools[tool.label] ?? false
                return (
                  <button
                    key={tool.label}
                    type="button"
                    title={tool.shortcut ? `${tool.label} (${tool.shortcut})` : tool.label}
                    aria-label={tool.label}
                    aria-pressed={isActive}
                    className={toolClass(isActive)}
                    // Keep the editor selection: the button must not take focus on press.
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => tool.run(editor)}
                  >
                    <Symbol src={tool.icon} />
                  </button>
                )
              })}
            </div>
          ))}
          <span className="mx-1 h-5 w-px bg-line" />
          <button
            type="button"
            title={active.link ? 'Убрать ссылку' : 'Ссылка'}
            aria-label={active.link ? 'Убрать ссылку' : 'Ссылка'}
            aria-pressed={active.link || linkOpen}
            className={toolClass(active.link || linkOpen)}
            onMouseDown={(event) => event.preventDefault()}
            onClick={toggleLink}
          >
            <Symbol src={link} />
          </button>
        </div>
        {linkOpen && <LinkForm editor={editor} onDone={() => setLinkOpen(false)} />}
        <EditorContent editor={editor} />
      </div>
      {error && <span className="text-sm text-negative">{error}</span>}
    </div>
  )
}
