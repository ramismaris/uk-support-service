import { Button } from '@maxhub/max-ui'
import { useState } from 'react'
import { RichTextField } from '@/features/rich-text-field'
import { ImagePicker, type ImageValue } from '@/features/upload-image'
import { ConfirmDialog } from '@/shared/ui/confirm-dialog'
import { plural } from '../lib/plural'
import { TEXT_LIMIT, toRequest, validateBroadcast, type Draft } from '../lib/validate'
import { useAudience, useSendBroadcast } from '../model/use-broadcasts'
import { AudiencePicker } from './AudiencePicker'

interface ComposeFormProps {
  draft: Draft
  photo: ImageValue | null
  // Another broadcast is still going out: the server accepts one at a time.
  busy: boolean
  onDraft: (draft: Draft) => void
  onPhoto: (photo: ImageValue | null) => void
  onSent: () => void
}

const residents = (count: number) => `${count} ${plural(count, 'жилец', 'жильца', 'жильцов')}`

export function ComposeForm({ draft, photo, busy, onDraft, onPhoto, onSent }: ComposeFormProps) {
  const [showErrors, setShowErrors] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const send = useSendBroadcast()

  const everyone = draft.scope === 'all'
  const audience = useAudience(everyone ? null : draft.buildingIds)
  const counting = everyone || draft.buildingIds.length > 0
  const count = counting ? audience.data?.count : undefined

  const errors = validateBroadcast(draft)
  const visibleErrors = showErrors ? errors : {}
  const nobody = count === 0

  const audienceText = () => {
    if (!counting) {
      return 'Выберите дома, чтобы увидеть число получателей'
    }
    if (audience.isError) {
      return audience.error.message
    }
    if (count === undefined) {
      return 'Считаем получателей…'
    }
    return nobody ? 'Получателей нет' : `Получат ${residents(count)}`
  }

  const submit = () => {
    setShowErrors(true)
    if (Object.keys(errors).length === 0) {
      setConfirming(true)
    }
  }

  const confirm = () =>
    send.mutate(toRequest(draft, photo?.id ?? null), {
      onSuccess: () => {
        setConfirming(false)
        setShowErrors(false)
        onSent()
      },
    })

  const cancel = () => {
    setConfirming(false)
    send.reset()
  }

  return (
    <form
      className="flex flex-col gap-6"
      onSubmit={(event) => {
        event.preventDefault()
        submit()
      }}
    >
      <RichTextField
        label="Текст"
        value={draft.text}
        limit={TEXT_LIMIT}
        error={visibleErrors.text}
        onChange={(text) => onDraft({ ...draft, text })}
      />
      <ImagePicker label="Фото (по желанию)" removable value={photo} onChange={onPhoto} />
      <AudiencePicker
        scope={draft.scope}
        buildingIds={draft.buildingIds}
        error={visibleErrors.buildings}
        onScope={(scope) => onDraft({ ...draft, scope })}
        onBuildingIds={(buildingIds) => onDraft({ ...draft, buildingIds })}
      />
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-line pt-4">
        <Button type="submit" disabled={busy || nobody}>
          Отправить
        </Button>
        <span className={`text-sm ${nobody ? 'text-negative' : 'text-fg-2'}`}>
          {audienceText()}
        </span>
        {busy && (
          <span className="basis-full text-sm text-fg-3">
            Другая рассылка ещё идёт: новую можно отправить, когда она закончится.
          </span>
        )}
      </div>
      <ConfirmDialog
        open={confirming}
        title="Отправить рассылку?"
        text={`${count === undefined ? 'Сообщение получат все выбранные жильцы' : `Сообщение получат ${residents(count)}`}. Отменить отправку будет нельзя.`}
        confirmLabel="Отправить"
        pending={send.isPending}
        error={send.error?.message}
        onConfirm={confirm}
        onCancel={cancel}
      />
    </form>
  )
}
