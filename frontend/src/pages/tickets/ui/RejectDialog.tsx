import { Button, Textarea } from '@maxhub/max-ui'
import { useEffect, useRef, useState } from 'react'
import { validateRejectReason } from '../lib/status-actions'

interface RejectDialogProps {
  open: boolean
  pending: boolean
  // Server error of the last attempt, shown inside the modal where the user is looking.
  serverError?: string
  onClose: () => void
  onConfirm: (reason: string) => void
}

export function RejectDialog({
  open,
  pending,
  serverError,
  onClose,
  onConfirm,
}: RejectDialogProps) {
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
      className="m-auto w-full max-w-md rounded-2xl bg-layer p-0 text-fg backdrop:bg-overlay"
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
        <p className="text-sm text-fg-3">Причину увидит жилец.</p>
        <Textarea
          value={reason}
          rows={4}
          autoFocus
          placeholder="Причина"
          onChange={(event) => setReason(event.target.value)}
        />
        {((touched && error) || serverError) && (
          <p role="alert" className="text-sm text-negative">
            {(touched && error) || serverError}
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
