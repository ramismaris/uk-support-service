import {
  Bold,
  Code,
  Highlighter,
  Italic,
  Link2,
  Strikethrough,
  Underline,
  type LucideIcon,
} from 'lucide-react'
import { useRef, type KeyboardEvent, type ReactNode } from 'react'
import { insertLink, toggleMarker, type Edit } from '../lib/format-edit'

const control =
  'w-full rounded-xl bg-fill px-3 py-2.5 text-[15px] leading-5 outline-none placeholder:text-fg-3 focus:ring-2 focus:ring-brand/40'

function Field({
  label,
  counter,
  error,
  children,
}: {
  label: string
  counter?: string
  error?: string
  children: ReactNode
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="flex items-baseline justify-between gap-2 text-sm">
        <span className="font-medium">{label}</span>
        {counter && <span className="text-xs text-fg-3">{counter}</span>}
      </span>
      {children}
      {error && <span className="text-sm text-negative">{error}</span>}
    </label>
  )
}

interface FormatTool {
  label: string
  icon: LucideIcon
  marker: string | null
  // Ctrl/⌘ + key, as in text editors.
  key?: string
}

// What Max renders in bot messages (dev.max.ru, text formatting).
const FORMAT_TOOLS: FormatTool[] = [
  { label: 'Жирный', icon: Bold, marker: '**', key: 'b' },
  { label: 'Курсив', icon: Italic, marker: '_', key: 'i' },
  { label: 'Подчёркнутый', icon: Underline, marker: '++', key: 'u' },
  { label: 'Зачёркнутый', icon: Strikethrough, marker: '~~' },
  { label: 'Моноширинный', icon: Code, marker: '`' },
  { label: 'Выделение', icon: Highlighter, marker: '^^' },
  { label: 'Ссылка', icon: Link2, marker: null, key: 'k' },
]

function FormattedTextarea({
  label,
  value,
  placeholder,
  onChange,
}: {
  label: string
  value: string
  placeholder?: string
  onChange: (value: string) => void
}) {
  const area = useRef<HTMLTextAreaElement>(null)

  const apply = (tool: FormatTool) => {
    const element = area.current
    if (!element) {
      return
    }
    const { selectionStart: start, selectionEnd: end } = element
    const edit: Edit =
      tool.marker === null
        ? insertLink(value, start, end)
        : toggleMarker(value, start, end, tool.marker)
    onChange(edit.value)
    // After React writes the new value, put the selection where the edit says.
    requestAnimationFrame(() => {
      element.focus()
      element.setSelectionRange(edit.start, edit.end)
    })
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey) {
      return
    }
    const tool = FORMAT_TOOLS.find((item) => item.key === event.key.toLowerCase())
    if (tool) {
      event.preventDefault()
      apply(tool)
    }
  }

  return (
    <div className="flex flex-col overflow-hidden rounded-xl bg-fill focus-within:ring-2 focus-within:ring-brand/40">
      <div role="toolbar" aria-label="Форматирование" className="flex flex-wrap gap-0.5 p-1">
        {FORMAT_TOOLS.map((tool) => {
          const Icon = tool.icon
          const hint = tool.key ? `${tool.label} (Ctrl+${tool.key.toUpperCase()})` : tool.label
          return (
            <button
              key={tool.label}
              type="button"
              title={hint}
              aria-label={tool.label}
              className="flex size-8 items-center justify-center rounded-lg text-fg-2 hover:bg-press hover:text-fg"
              // Keep the textarea selection: the button must not take focus on press.
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => apply(tool)}
            >
              <Icon size={16} strokeWidth={2.25} />
            </button>
          )
        })}
      </div>
      <textarea
        ref={area}
        // The wrapping <label> would name the first toolbar button instead.
        aria-label={label}
        value={value}
        rows={6}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
        className="w-full resize-y bg-transparent px-3 pt-1 pb-2.5 text-[15px] leading-5 outline-none placeholder:text-fg-3"
      />
    </div>
  )
}

interface TextFieldProps {
  label: string
  value: string
  limit: number
  onChange: (value: string) => void
  error?: string
  multiline?: boolean
  // Toolbar for Max markdown; only for texts the bot sends with formatting.
  formatting?: boolean
  placeholder?: string
}

export function TextField({
  label,
  value,
  limit,
  onChange,
  error,
  multiline = false,
  formatting = false,
  placeholder,
}: TextFieldProps) {
  return (
    <Field label={label} counter={`${value.length}/${limit}`} error={error}>
      {formatting ? (
        <FormattedTextarea
          label={label}
          value={value}
          placeholder={placeholder}
          onChange={onChange}
        />
      ) : multiline ? (
        <textarea
          value={value}
          rows={6}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          className={`${control} resize-y`}
        />
      ) : (
        <input
          value={value}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          className={control}
        />
      )}
    </Field>
  )
}
