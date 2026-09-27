import { Button } from '@maxhub/max-ui'
import { ChevronLeft, FileQuestion, Plus, SearchX, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useBlocker, useParams } from 'react-router'
import { ImagePicker } from '@/features/upload-image'
import { routePaths } from '@/shared/config'
import { ConfirmDialog } from '@/shared/ui/confirm-dialog'
import { EmptyState } from '@/shared/ui/empty-state'
import { draftSignature, isDirty } from '../lib/dirty'
import { botPreview } from '../lib/preview'
import {
  draftsFromContent,
  isSection,
  sectionTitles,
  type ContactPhone,
  type Drafts,
  type Section,
} from '../lib/sections'
import { validateSection } from '../lib/validate'
import { useContent, useSaveSection } from '../model/use-content'
import { BotPreview } from './BotPreview'
import { TextField } from './fields'

const SAVED_VISIBLE_MS = 2000
const MAX_PHONES = 10

type AnyDraft = Drafts[Section]

interface FormProps {
  section: Section
  saved: AnyDraft
  // Kept by the parent: saving refetches the content and remounts the form.
  justSaved: boolean
  onSaved: (saved: boolean) => void
}

function PhoneInput({
  value,
  label,
  placeholder,
  inputMode,
  error,
  onChange,
}: {
  value: string
  label: string
  placeholder: string
  inputMode?: 'tel'
  error?: string
  onChange: (value: string) => void
}) {
  return (
    <div className="flex min-w-0 flex-1 flex-col gap-1">
      <input
        value={value}
        aria-label={label}
        aria-invalid={error ? true : undefined}
        placeholder={placeholder}
        inputMode={inputMode}
        onChange={(event) => onChange(event.target.value)}
        className="min-w-0 rounded-xl bg-fill px-3 py-2.5 text-[15px] outline-none placeholder:text-fg-3 focus:ring-2 focus:ring-brand/40"
      />
      {error && <span className="text-sm text-negative">{error}</span>}
    </div>
  )
}

function PhonesField({
  phones,
  errors,
  onChange,
}: {
  phones: ContactPhone[]
  errors: Record<string, string>
  onChange: (phones: ContactPhone[]) => void
}) {
  const update = (index: number, patch: Partial<ContactPhone>) =>
    onChange(phones.map((phone, i) => (i === index ? { ...phone, ...patch } : phone)))

  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-medium">Телефоны</span>
      {phones.map((phone, index) => (
        <div key={index} className="flex items-start gap-2">
          <div className="flex min-w-0 flex-1 flex-col gap-1 sm:flex-row">
            <PhoneInput
              value={phone.title}
              label="Подпись"
              placeholder="Подпись, например «Диспетчер»"
              error={errors[`phones.${index}.title`]}
              onChange={(title) => update(index, { title })}
            />
            <PhoneInput
              value={phone.phone}
              label="Номер"
              placeholder="+7 900 000-00-00"
              inputMode="tel"
              error={errors[`phones.${index}.phone`]}
              onChange={(value) => update(index, { phone: value })}
            />
          </div>
          <button
            type="button"
            aria-label="Удалить телефон"
            onClick={() => onChange(phones.filter((_, i) => i !== index))}
            className="flex size-10 shrink-0 items-center justify-center rounded-xl text-fg-3 hover:bg-hover hover:text-negative"
          >
            <Trash2 size={18} strokeWidth={2} />
          </button>
        </div>
      ))}
      {errors.phones && <span className="text-sm text-negative">{errors.phones}</span>}
      {phones.length < MAX_PHONES && (
        <button
          type="button"
          onClick={() => onChange([...phones, { title: '', phone: '' }])}
          className="flex items-center gap-1.5 self-start rounded-lg px-2 py-1.5 text-sm font-medium text-brand hover:bg-hover"
        >
          <Plus size={16} strokeWidth={2} />
          Добавить телефон
        </button>
      )}
    </div>
  )
}

function SectionForm({ section, saved, justSaved, onSaved }: FormProps) {
  const [draft, setDraft] = useState<AnyDraft>(saved)
  const [showErrors, setShowErrors] = useState(false)
  const save = useSaveSection(section)

  const errors = useMemo(() => validateSection(section, draft), [section, draft])
  const dirty = isDirty(saved, draft)
  const valid = Object.keys(errors).length === 0
  const visibleErrors = showErrors ? errors : {}

  // Leaving with unsaved changes asks first (in-app navigation and closing the tab).
  const blocker = useBlocker(({ currentLocation, nextLocation }) => {
    return dirty && !save.isPending && currentLocation.pathname !== nextLocation.pathname
  })
  useEffect(() => {
    if (!dirty) {
      return
    }
    const warn = (event: BeforeUnloadEvent) => event.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])

  const patch = (changes: Partial<AnyDraft>) => {
    setDraft({ ...draft, ...changes } as AnyDraft)
    onSaved(false)
  }

  const submit = () => {
    setShowErrors(true)
    if (!valid) {
      return
    }
    save.mutate(draft as never, { onSuccess: () => onSaved(true) })
  }

  const preview = botPreview(section, draft as never)

  return (
    // On wide screens the form and the preview stay together in the middle, as does the title.
    <div className="mx-auto grid w-full max-w-[66.5rem] gap-6 p-4 lg:p-6 xl:grid-cols-[minmax(0,42rem)_20rem]">
      <form
        className="flex max-w-2xl flex-col gap-5"
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        {section === 'welcome' && (
          <ImagePicker
            label="Фото"
            value={(draft as Drafts['welcome']).photo}
            onChange={(photo) => patch({ photo } as Partial<AnyDraft>)}
            error={visibleErrors.photo}
          />
        )}
        <TextField
          label="Текст"
          multiline
          value={draft.text}
          limit={3000}
          error={visibleErrors.text}
          onChange={(text) => patch({ text })}
        />
        {section === 'payment' && (
          <>
            <TextField
              label="Ссылка на оплату"
              value={(draft as Drafts['payment']).url}
              limit={2048}
              placeholder="https://"
              error={visibleErrors.url}
              onChange={(url) => patch({ url } as Partial<AnyDraft>)}
            />
            <TextField
              label="Текст кнопки"
              value={(draft as Drafts['payment']).buttonText}
              limit={64}
              placeholder="Оплатить"
              error={visibleErrors.buttonText}
              onChange={(buttonText) => patch({ buttonText } as Partial<AnyDraft>)}
            />
          </>
        )}
        {section === 'contacts' && (
          <PhonesField
            phones={(draft as Drafts['contacts']).phones}
            errors={visibleErrors}
            onChange={(phones) => patch({ phones } as Partial<AnyDraft>)}
          />
        )}
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={!dirty || save.isPending} loading={save.isPending}>
            Сохранить
          </Button>
          {justSaved && (
            <span className="text-sm text-fg-2">Сохранено — бот уже показывает новое</span>
          )}
          {save.error && (
            <span role="alert" className="text-sm text-negative">
              {save.error.message}
            </span>
          )}
        </div>
      </form>
      <aside className="xl:sticky xl:top-6 xl:self-start">
        <BotPreview preview={preview} section={sectionTitles[section]} />
      </aside>
      <ConfirmDialog
        open={blocker.state === 'blocked'}
        title="Уйти без сохранения?"
        text="Изменения в этом разделе пропадут."
        confirmLabel="Уйти"
        destructive
        onConfirm={() => blocker.proceed?.()}
        onCancel={() => blocker.reset?.()}
      />
    </div>
  )
}

export function SectionEditor() {
  const { section: param } = useParams()
  const section: Section | null = param === undefined ? 'welcome' : isSection(param) ? param : null
  const content = useContent()
  const [savedSection, setSavedSection] = useState<Section | null>(null)

  useEffect(() => {
    if (!savedSection) {
      return
    }
    const timer = setTimeout(() => setSavedSection(null), SAVED_VISIBLE_MS)
    return () => clearTimeout(timer)
  }, [savedSection])

  if (section === null) {
    return (
      <EmptyState
        icon={<FileQuestion size={48} strokeWidth={1.5} />}
        title="Раздел не найден"
        action={
          <Button asChild variant="secondary">
            <Link to={routePaths.content}>К разделам</Link>
          </Button>
        }
      />
    )
  }
  if (content.isPending) {
    return <div className="m-auto text-sm text-fg-3">Загрузка…</div>
  }
  if (content.isError) {
    return (
      <EmptyState
        icon={<SearchX size={48} strokeWidth={1.5} />}
        title="Не удалось загрузить контент"
        text={content.error.message}
        action={<Button onClick={() => void content.refetch()}>Повторить</Button>}
      />
    )
  }

  const saved = draftsFromContent(content.data)[section]
  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-y-auto">
      <header className="border-b border-line px-3 py-3 lg:px-6">
        <div className="mx-auto flex w-full max-w-[63.5rem] items-center gap-2">
          <Link
            to={routePaths.content}
            aria-label="К разделам"
            className="-ml-1 rounded-full p-1 hover:bg-hover lg:hidden"
          >
            <ChevronLeft size={20} strokeWidth={2} />
          </Link>
          <h1 className="text-lg font-semibold">{sectionTitles[section]}</h1>
        </div>
      </header>
      {/* Remount on section change and after saving, so the draft starts from the saved data. */}
      <SectionForm
        key={`${section}:${draftSignature(saved)}`}
        section={section}
        saved={saved}
        justSaved={savedSection === section}
        onSaved={(done) => setSavedSection(done ? section : null)}
      />
    </section>
  )
}
