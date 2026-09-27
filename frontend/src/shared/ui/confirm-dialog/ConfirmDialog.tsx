import { Button } from '@maxhub/max-ui'
import { useEffect, useRef } from 'react'

interface ConfirmDialogProps {
  open: boolean
  title: string
  text: string
  confirmLabel: string
  destructive?: boolean
  pending?: boolean
  error?: string | null
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  text,
  confirmLabel,
  destructive = false,
  pending = false,
  error,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialog = useRef<HTMLDialogElement>(null)

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
      onClose={onCancel}
      className="m-auto w-[calc(100%-2rem)] max-w-sm rounded-2xl bg-layer p-0 text-fg backdrop:bg-overlay"
    >
      <div className="flex flex-col gap-3 p-5">
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="text-sm text-fg-2">{text}</p>
        {error && (
          <p role="alert" className="text-sm text-negative">
            {error}
          </p>
        )}
        {/* Buttons keep their full labels and wrap instead of cutting to "Отме…". */}
        <div className="flex flex-wrap justify-end gap-2 pt-1 *:shrink-0">
          <Button type="button" variant="secondary" onClick={onCancel}>
            Отмена
          </Button>
          <Button
            type="button"
            variant={destructive ? 'destructive' : 'primary'}
            loading={pending}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </dialog>
  )
}
