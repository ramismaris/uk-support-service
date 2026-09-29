import { Button } from '@maxhub/max-ui'
import { motion, useReducedMotion, type Variants } from 'framer-motion'
import { Eye, History as HistoryIcon, Megaphone, SearchX } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useDraftKey } from '@/entities/session'
import type { ImageValue } from '@/features/upload-image'
import { browserStorage, clearDraft, readDraft, useDraftSaver } from '@/shared/lib/drafts'
import { Card } from '@/shared/ui/card'
import { BotMessage } from '@/shared/ui/bot-message'
import { DraftNotice } from '@/shared/ui/draft-notice'
import { EmptyState } from '@/shared/ui/empty-state'
import { NavMenuButton } from '@/widgets/app-shell'
import {
  isBroadcastEmpty,
  parseBroadcastDraft,
  restoreBroadcast,
  type BroadcastDraftState,
} from '../lib/persisted'
import type { Draft } from '../lib/validate'
import { useBroadcasts } from '../model/use-broadcasts'
import { ComposeForm } from './ComposeForm'
import { History } from './History'

const stagger: Variants = { shown: { transition: { staggerChildren: 0.06 } } }

const EMPTY_DRAFT: Draft = { text: '', scope: 'all', buildingIds: [] }

const MAIN_MENU_BUTTON = [{ label: 'Главное меню' }]

function Preview({ draft, photo }: { draft: Draft; photo: ImageValue | null }) {
  return (
    <Card title="Так увидит жилец" icon={Eye}>
      <div className="rounded-xl bg-surface p-4">
        <BotMessage
          text={draft.text}
          photoUrl={photo?.url}
          buttons={MAIN_MENU_BUTTON}
          placeholder="Текст рассылки"
        />
      </div>
    </Card>
  )
}

function readSaved(key: string | null): BroadcastDraftState | null {
  const envelope = key && readDraft(browserStorage(), key, parseBroadcastDraft)
  return envelope ? restoreBroadcast(envelope) : null
}

export function BroadcastPage() {
  const reduceMotion = useReducedMotion()
  const history = useBroadcasts()
  const storageKey = useDraftKey('broadcast')
  const [saved] = useState(() => readSaved(storageKey))
  const [draft, setDraft] = useState<Draft>(saved?.draft ?? EMPTY_DRAFT)
  const [photo, setPhoto] = useState<ImageValue | null>(saved?.photo ?? null)
  const [restored, setRestored] = useState(saved !== null)
  // A new key remounts the form, and with it the editor, which reads its text only once.
  const [formKey, setFormKey] = useState(0)

  const state = useMemo(() => ({ draft, photo }), [draft, photo])
  useDraftSaver(storageKey, state, isBroadcastEmpty)

  const busy = history.data?.items.some((item) => item.status === 'SENDING') ?? false

  const clear = () => {
    if (storageKey) {
      clearDraft(browserStorage(), storageKey)
    }
    setDraft(EMPTY_DRAFT)
    setPhoto(null)
    setRestored(false)
    setFormKey(formKey + 1)
  }

  const historyBody = () => {
    if (history.isPending) {
      return <div className="h-24 animate-pulse rounded-xl bg-fill" />
    }
    if (history.isError) {
      return (
        <EmptyState
          icon={<SearchX size={48} strokeWidth={1.5} />}
          title="Не удалось загрузить историю"
          text={history.error.message}
          action={<Button onClick={() => void history.refetch()}>Повторить</Button>}
        />
      )
    }
    return <History items={history.data.items} />
  }

  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-y-auto">
      <header className="border-b border-line px-3 py-3 lg:px-6">
        <div className="flex items-center gap-2">
          <NavMenuButton />
          <h1 className="text-lg font-semibold">Рассылка</h1>
        </div>
      </header>
      <motion.div
        className="grid items-start gap-4 p-4 lg:p-6 xl:grid-cols-[minmax(0,1fr)_22rem]"
        variants={stagger}
        initial={reduceMotion ? false : 'hidden'}
        animate="shown"
      >
        <Card title="Новая рассылка" icon={Megaphone} bodyClassName="gap-4 p-5">
          {restored && <DraftNotice onReset={clear} />}
          <ComposeForm
            key={formKey}
            draft={draft}
            photo={photo}
            busy={busy}
            onDraft={setDraft}
            onPhoto={setPhoto}
            onSent={clear}
          />
        </Card>
        <div className="xl:sticky xl:top-6">
          <Preview draft={draft} photo={photo} />
        </div>
        <Card title="История" icon={HistoryIcon} className="xl:col-span-2">
          {historyBody()}
        </Card>
      </motion.div>
    </section>
  )
}
