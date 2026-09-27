import { Button } from '@maxhub/max-ui'
import { FileText, Plus, X } from 'lucide-react'
import { useEffect, useRef, type KeyboardEvent } from 'react'
import { formatFileSize } from '@/shared/lib/format'
import { attachTitle, isImage, pastedImages } from '../lib/attach'
import { MESSAGE_TEXT_LIMIT } from '../lib/message-rules'

// A local preview of a picked file; the object URL lives as long as the thumbnail.
function Preview({ file, className }: { file: File; className: string }) {
  const img = useRef<HTMLImageElement>(null)
  useEffect(() => {
    const url = URL.createObjectURL(file)
    if (img.current) {
      img.current.src = url
    }
    return () => URL.revokeObjectURL(url)
  }, [file])
  return <img ref={img} alt={file.name} className={className} />
}

function RemoveButton({ name, onClick }: { name: string; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-label={`Убрать ${name}`}
      className="flex size-7 items-center justify-center rounded-full bg-black/55 text-white hover:bg-black/70"
      onClick={onClick}
    >
      <X size={16} strokeWidth={2} />
    </button>
  )
}

interface AttachDialogProps {
  files: File[]
  caption: string
  error: string | null
  pending: boolean
  canSend: boolean
  onCaptionChange: (caption: string) => void
  onAdd: (files: File[]) => void
  onRemove: (index: number) => void
  onCancel: () => void
  onSend: () => void
}

// Like Telegram: picked files open in a preview with a caption before they go to the resident.
export function AttachDialog({
  files,
  caption,
  error,
  pending,
  canSend,
  onCaptionChange,
  onAdd,
  onRemove,
  onCancel,
  onSend,
}: AttachDialogProps) {
  const dialog = useRef<HTMLDialogElement>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const captionInput = useRef<HTMLTextAreaElement>(null)
  const open = files.length > 0

  useEffect(() => {
    const element = dialog.current
    if (open && !element?.open) {
      element?.showModal()
      // showModal focuses the first button (a remove cross); Enter must send, not remove.
      captionInput.current?.focus()
    }
    if (!open && element?.open) {
      element.close()
    }
  }, [open])

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      onSend()
    }
  }

  const photos = files.every(isImage)

  return (
    <dialog
      ref={dialog}
      onClose={onCancel}
      aria-label={open ? attachTitle(files) : undefined}
      className="m-auto w-[calc(100%-2rem)] max-w-md rounded-2xl bg-layer p-0 text-fg backdrop:bg-overlay"
    >
      {open && (
        <div className="flex flex-col gap-3 p-4">
          <h2 className="text-lg font-semibold">{attachTitle(files)}</h2>

          {photos && files.length === 1 ? (
            <div className="relative overflow-hidden rounded-xl bg-fill">
              <Preview file={files[0]!} className="max-h-80 w-full object-contain" />
              <div className="absolute top-2 right-2">
                <RemoveButton name={files[0]!.name} onClick={() => onRemove(0)} />
              </div>
            </div>
          ) : (
            <ul className={photos ? 'grid grid-cols-3 gap-1' : 'flex flex-col gap-2'}>
              {files.map((file, index) =>
                isImage(file) ? (
                  <li
                    key={`${file.name}-${index}`}
                    className="relative aspect-square overflow-hidden rounded-lg bg-fill"
                  >
                    <Preview file={file} className="size-full object-cover" />
                    <div className="absolute top-1 right-1">
                      <RemoveButton name={file.name} onClick={() => onRemove(index)} />
                    </div>
                  </li>
                ) : (
                  <li
                    key={`${file.name}-${index}`}
                    className="flex items-center gap-3 rounded-xl bg-fill px-3 py-2"
                  >
                    <FileText size={24} strokeWidth={2} className="shrink-0 text-fg-3" />
                    <div className="min-w-0 flex-1">
                      <div className="text-sm break-all">{file.name}</div>
                      <div className="text-xs text-fg-3">{formatFileSize(file.size)}</div>
                    </div>
                    <button
                      type="button"
                      aria-label={`Убрать ${file.name}`}
                      className="rounded-full p-1.5 text-fg-3 hover:bg-press hover:text-fg"
                      onClick={() => onRemove(index)}
                    >
                      <X size={18} strokeWidth={2} />
                    </button>
                  </li>
                ),
              )}
            </ul>
          )}

          <textarea
            ref={captionInput}
            value={caption}
            rows={2}
            maxLength={MESSAGE_TEXT_LIMIT + 1}
            placeholder="Подпись"
            disabled={pending}
            className="max-h-32 resize-none rounded-xl bg-fill px-3 py-2 text-[15px] leading-5 outline-none placeholder:text-fg-3"
            onChange={(event) => onCaptionChange(event.target.value)}
            onKeyDown={onKeyDown}
            onPaste={(event) => {
              const images = pastedImages(Array.from(event.clipboardData.files))
              if (images.length > 0) {
                event.preventDefault()
                onAdd(images)
              }
            }}
          />

          {error && (
            <p role="alert" className="text-sm text-negative">
              {error}
            </p>
          )}

          <div className="flex flex-wrap items-center justify-end gap-2 *:shrink-0">
            <button
              type="button"
              disabled={pending}
              className="mr-auto flex items-center gap-1 rounded-full px-2 py-1.5 text-sm font-medium text-brand hover:bg-press"
              onClick={() => fileInput.current?.click()}
            >
              <Plus size={18} strokeWidth={2} />
              Добавить
            </button>
            <input
              ref={fileInput}
              type="file"
              multiple
              hidden
              onChange={(event) => {
                onAdd(Array.from(event.target.files ?? []))
                event.target.value = ''
              }}
            />
            <Button type="button" variant="secondary" disabled={pending} onClick={onCancel}>
              Отмена
            </Button>
            <Button type="button" loading={pending} disabled={!canSend} onClick={onSend}>
              Отправить
            </Button>
          </div>
        </div>
      )}
    </dialog>
  )
}
