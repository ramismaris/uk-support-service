import { Button } from '@maxhub/max-ui'
import { motion, useReducedMotion, type Variants } from 'framer-motion'
import { Eye, History as HistoryIcon, Megaphone, SearchX } from 'lucide-react'
import { useState } from 'react'
import type { ImageValue } from '@/features/upload-image'
import { Card } from '@/shared/ui/card'
import { BotMessage } from '@/shared/ui/bot-message'
import { EmptyState } from '@/shared/ui/empty-state'
import { NavMenuButton } from '@/widgets/app-shell'
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

export function BroadcastPage() {
  const reduceMotion = useReducedMotion()
  const history = useBroadcasts()
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT)
  const [photo, setPhoto] = useState<ImageValue | null>(null)
  // A new key remounts the form, and with it the editor, which reads its text only once.
  const [formKey, setFormKey] = useState(0)

  const busy = history.data?.items.some((item) => item.status === 'SENDING') ?? false

  const sent = () => {
    setDraft(EMPTY_DRAFT)
    setPhoto(null)
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
        <Card title="Новая рассылка" icon={Megaphone} bodyClassName="p-5">
          <ComposeForm
            key={formKey}
            draft={draft}
            photo={photo}
            busy={busy}
            onDraft={setDraft}
            onPhoto={setPhoto}
            onSent={sent}
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
