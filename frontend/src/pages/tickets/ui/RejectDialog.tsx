import { Button, Textarea } from '@maxhub/max-ui'
import { useEffect, useRef, useState } from 'react'
import { validateRejectReason } from '../lib/status-actions'

interface RejectDialogProps {
  open: boolean
  pending: boolean
  onClose: () => void
  onConfirm: (reason: string) => void
}

export function RejectDialog({ open, pending, onClose, onConfirm }: RejectDialogProps) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [reason, setReason] = useState('')
  const [touched, setTouched] = useState(false)
  const error = validateRejectReason(reason)

  useEffect(() => {
    const element = dialog.current
    if (open && !element?.open) {
      element?.showModal()
    }
    if (!open && element?.open) {
      element.close()
    }
  }, [open])

  return (
    <dialog
      ref={dialog}
      onClose={onClose}
      className="m-auto w-full max-w-md rounded-2xl bg-white p-0 text-neutral-900 backdrop:bg-black/40 dark:bg-neutral-900 dark:text-neutral-100"
    >
      <form
        method="dialog"
        className="flex flex-col gap-3 p-5"
        onSubmit={(event) => {
          event.preventDefault()
          setTouched(true)
          if (error === null) {
            onConfirm(reason.trim())
          }
        }}
      >
        <h2 className="text-lg font-semibold">Отклонить обращение</h2>
        <p className="text-sm text-neutral-500">Причину увидит жилец.</p>
        <Textarea
          value={reason}
          rows={4}
          autoFocus
          placeholder="Причина"
          onChange={(event) => setReason(event.target.value)}
        />
        {touched && error && (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Отмена
          </Button>
          <Button type="submit" variant="destructive" loading={pending}>
            Отклонить
          </Button>
        </div>
      </form>
    </dialog>
  )
}
