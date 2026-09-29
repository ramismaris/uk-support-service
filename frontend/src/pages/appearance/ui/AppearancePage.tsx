import { Button } from '@maxhub/max-ui'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, SearchX, TriangleAlert } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useDraftKey } from '@/entities/session'
import {
  applyTheme,
  themeFromResponse,
  themeKeys,
  useTheme,
  type ThemeResponse,
} from '@/entities/theme'
import { ImagePicker, type ImageValue } from '@/features/upload-image'
import { contrastWithWhite, LOW_CONTRAST } from '@/shared/lib/color'
import { browserStorage, clearDraft, readDraft, useDraftSaver } from '@/shared/lib/drafts'
import { DraftNotice } from '@/shared/ui/draft-notice'
import { EmptyState } from '@/shared/ui/empty-state'
import { NavMenuButton } from '@/widgets/app-shell'
import { saveTheme } from '../api/save-theme'
import { PALETTE } from '../lib/palette'
import { restoreTheme, storableTheme } from '../lib/persisted'
import { NAME_LIMIT, validateTheme } from '../lib/validate'
import { ColorPicker } from './ColorPicker'
import { ThemePreview } from './ThemePreview'

const SAVED_VISIBLE_MS = 2000

const control =
  'rounded-xl bg-fill px-3 py-2.5 text-[15px] leading-5 outline-none placeholder:text-fg-3 focus:ring-2 focus:ring-brand/40'

interface Draft {
  companyName: string
  primaryColor: string
  logo: ImageValue | null
}

function draftFromResponse(response: ThemeResponse | null): Draft {
  const theme = themeFromResponse(response)
  const logoId = response?.logo_file_id ?? null
  return {
    companyName: response ? theme.companyName : '',
    primaryColor: theme.primaryColor,
    logo: logoId !== null && theme.logoUrl ? { id: logoId, url: theme.logoUrl } : null,
  }
}

function sameDraft(a: Draft, b: Draft): boolean {
  return (
    a.companyName === b.companyName &&
    a.primaryColor.toLowerCase() === b.primaryColor.toLowerCase() &&
    (a.logo?.id ?? null) === (b.logo?.id ?? null)
  )
}

interface FormProps {
  saved: Draft
  // Kept by the parent: saving updates the theme and remounts the form.
  justSaved: boolean
  onSaved: (saved: boolean) => void
}

function readSaved(key: string | null, saved: Draft): Draft | null {
  const envelope = key && readDraft(browserStorage(), key, (raw) => raw)
  const restored = envelope ? restoreTheme(saved, envelope.data) : null
  return restored && !sameDraft(saved, restored) ? restored : null
}

function ThemeForm({ saved, justSaved, onSaved }: FormProps) {
  const queryClient = useQueryClient()
  const storageKey = useDraftKey('appearance')
  const [restoredDraft] = useState(() => readSaved(storageKey, saved))
  const [draft, setDraft] = useState(restoredDraft ?? saved)
  const [restored, setRestored] = useState(restoredDraft !== null)
  const [showErrors, setShowErrors] = useState(false)

  const storable = useMemo(() => storableTheme(draft), [draft])
  useDraftSaver(storageKey, storable, (value) => sameDraft(saved, { ...saved, ...value }))

  const forgetDraft = () => {
    if (storageKey) {
      clearDraft(browserStorage(), storageKey)
    }
  }

  const resetDraft = () => {
    forgetDraft()
    setDraft(saved)
    setRestored(false)
  }

  const save = useMutation({
    mutationFn: saveTheme,
    onSuccess: (response) => {
      forgetDraft()
      queryClient.setQueryData(themeKeys.current, response)
      applyTheme(themeFromResponse(response))
      onSaved(true)
    },
  })

  const errors = validateTheme(draft)
  const visibleErrors = showErrors ? errors : {}
  const dirty = !sameDraft(saved, draft)
  const colorValid = errors.primaryColor === undefined
  const contrast = colorValid ? contrastWithWhite(draft.primaryColor) : null

  const patch = (changes: Partial<Draft>) => {
    setDraft({ ...draft, ...changes })
    onSaved(false)
  }

  const submit = () => {
    setShowErrors(true)
    if (Object.keys(errors).length > 0) {
      return
    }
    save.mutate({
      companyName: draft.companyName,
      primaryColor: draft.primaryColor,
      logoFileId: draft.logo?.id ?? null,
    })
  }

  return (
    <div className="mx-auto grid w-full max-w-[61rem] gap-8 p-4 lg:p-6 xl:grid-cols-[minmax(0,36rem)_20rem]">
      <form
        className="flex max-w-xl flex-col gap-6"
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        {restored && <DraftNotice onReset={resetDraft} />}
        <label className="flex flex-col gap-1.5">
          <span className="flex items-baseline justify-between gap-2 text-sm">
            <span className="font-medium">Название компании</span>
            <span className="text-xs text-fg-3">
              {draft.companyName.length}/{NAME_LIMIT}
            </span>
          </span>
          <input
            value={draft.companyName}
            placeholder="УК «Наш дом»"
            onChange={(event) => patch({ companyName: event.target.value })}
            className={control}
          />
          <span className="text-xs text-fg-3">
            Видно в меню панели, на входе и во вкладке браузера
          </span>
          {visibleErrors.companyName && (
            <span className="text-sm text-negative">{visibleErrors.companyName}</span>
          )}
        </label>

        <fieldset className="flex flex-col gap-3">
          <legend className="mb-1.5 text-sm font-medium">Фирменный цвет</legend>
          <div role="radiogroup" aria-label="Готовые цвета" className="flex flex-wrap gap-1.5">
            {PALETTE.map((color) => {
              const selected = color.hex === draft.primaryColor.toLowerCase()
              return (
                <button
                  key={color.hex}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  aria-label={color.name}
                  title={color.name}
                  onClick={() => patch({ primaryColor: color.hex })}
                  style={{ backgroundColor: color.hex }}
                  className={`flex size-9 items-center justify-center rounded-full text-white transition-transform hover:scale-105 ${
                    selected ? 'ring-2 ring-fg ring-offset-2 ring-offset-layer' : ''
                  }`}
                >
                  {selected && <Check size={18} strokeWidth={2.5} />}
                </button>
              )
            })}
          </div>
          <div className="flex items-center gap-2 self-start">
            <ColorPicker
              value={draft.primaryColor}
              valid={colorValid}
              onChange={(primaryColor) => patch({ primaryColor })}
            />
            <input
              value={draft.primaryColor}
              aria-label="Свой цвет"
              placeholder="#RRGGBB"
              maxLength={7}
              spellCheck={false}
              onChange={(event) => {
                const value = event.target.value.trim()
                patch({ primaryColor: value.startsWith('#') ? value : `#${value}` })
              }}
              className={`${control} w-32 font-mono uppercase`}
            />
          </div>
          {visibleErrors.primaryColor && (
            <span className="text-sm text-negative">{visibleErrors.primaryColor}</span>
          )}
          {contrast !== null && contrast < LOW_CONTRAST && (
            <p className="flex items-start gap-2 rounded-xl bg-attention/10 px-3 py-2 text-sm">
              <TriangleAlert size={16} strokeWidth={2} className="mt-0.5 shrink-0 text-attention" />
              <span>
                Белый текст на этом цвете читается плохо (контраст {contrast.toFixed(1)}:1). Лучше
                выбрать цвет темнее.
              </span>
            </p>
          )}
        </fieldset>

        <ImagePicker
          label="Логотип"
          shape="square"
          removable
          value={draft.logo}
          onChange={(logo) => patch({ logo })}
        />

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={!dirty || save.isPending} loading={save.isPending}>
            Сохранить
          </Button>
          {justSaved && (
            <span className="text-sm text-fg-2">Сохранено — панель уже в новом цвете</span>
          )}
          {save.error && (
            <span role="alert" className="text-sm text-negative">
              {save.error.message}
            </span>
          )}
        </div>
      </form>
      <aside className="xl:sticky xl:top-6 xl:self-start">
        <ThemePreview
          companyName={draft.companyName}
          primaryColor={colorValid ? draft.primaryColor : saved.primaryColor}
          logoUrl={draft.logo?.url ?? null}
        />
      </aside>
    </div>
  )
}

export function AppearancePage() {
  const theme = useTheme()
  const [justSaved, setJustSaved] = useState(false)

  useEffect(() => {
    if (!justSaved) {
      return
    }
    const timer = setTimeout(() => setJustSaved(false), SAVED_VISIBLE_MS)
    return () => clearTimeout(timer)
  }, [justSaved])

  const body = () => {
    if (theme.isPending) {
      return <div className="m-auto text-sm text-fg-3">Загрузка…</div>
    }
    if (theme.isError) {
      return (
        <EmptyState
          icon={<SearchX size={48} strokeWidth={1.5} />}
          title="Не удалось загрузить оформление"
          text={theme.error.message}
          action={<Button onClick={() => void theme.refetch()}>Повторить</Button>}
        />
      )
    }
    const saved = draftFromResponse(theme.data)
    // Remount after saving, so the form starts from what the server stored.
    return (
      <ThemeForm
        key={`${saved.companyName}|${saved.primaryColor}|${saved.logo?.id ?? ''}`}
        saved={saved}
        justSaved={justSaved}
        onSaved={setJustSaved}
      />
    )
  }

  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-y-auto">
      <header className="border-b border-line px-3 py-3 lg:px-6">
        <div className="mx-auto flex w-full max-w-[58rem] items-center gap-2">
          <NavMenuButton />
          <h1 className="text-lg font-semibold">Оформление</h1>
        </div>
      </header>
      {body()}
    </section>
  )
}
