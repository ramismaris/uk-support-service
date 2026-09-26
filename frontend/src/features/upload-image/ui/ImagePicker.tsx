import { ImagePlus, LoaderCircle, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { validateImage } from '../lib/validate-image'
import { useUploadImage } from '../model/use-upload-image'

export interface ImageValue {
  id: number
  url: string
}

interface ImagePickerProps {
  value: ImageValue | null
  onChange: (value: ImageValue | null) => void
  label: string
  // Shown when the form requires an image and none is set.
  error?: string
  removable?: boolean
  // Preview box shape: a photo is wide, a logo is square.
  shape?: 'wide' | 'square'
}

export function ImagePicker({
  value,
  onChange,
  label,
  error,
  removable = false,
  shape = 'wide',
}: ImagePickerProps) {
  const input = useRef<HTMLInputElement>(null)
  const upload = useUploadImage()
  const [localError, setLocalError] = useState<string | null>(null)
  const box = shape === 'wide' ? 'h-32 w-48' : 'size-24'

  const pick = (file: File | undefined) => {
    if (!file) {
      return
    }
    const problem = validateImage(file)
    setLocalError(problem)
    if (problem) {
      return
    }
    upload.mutate(file, { onSuccess: (image) => onChange({ id: image.id, url: image.url }) })
  }

  const shownError = localError ?? upload.error?.message ?? error

  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-medium">{label}</span>
      <div className="flex items-end gap-3">
        <button
          type="button"
          onClick={() => input.current?.click()}
          disabled={upload.isPending}
          className={`${box} relative flex shrink-0 items-center justify-center overflow-hidden rounded-xl bg-fill text-fg-3 transition-colors hover:bg-press`}
        >
          {value ? (
            <img src={value.url} alt="" className="size-full object-cover" />
          ) : (
            <ImagePlus size={24} strokeWidth={2} />
          )}
          {upload.isPending && (
            <span className="absolute inset-0 flex items-center justify-center bg-overlay text-white">
              <LoaderCircle size={22} strokeWidth={2} className="animate-spin" />
            </span>
          )}
        </button>
        <div className="flex flex-col items-start gap-1 text-sm">
          <button
            type="button"
            onClick={() => input.current?.click()}
            disabled={upload.isPending}
            className="font-medium text-brand hover:underline"
          >
            {value ? 'Заменить' : 'Загрузить'}
          </button>
          {value && removable && (
            <button
              type="button"
              onClick={() => onChange(null)}
              className="flex items-center gap-1 text-fg-3 hover:text-fg"
            >
              <X size={14} strokeWidth={2} />
              Убрать
            </button>
          )}
          <span className="text-xs text-fg-3">JPEG или PNG, до 20 МБ</span>
        </div>
      </div>
      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png"
        hidden
        onChange={(event) => {
          pick(event.target.files?.[0])
          event.target.value = ''
        }}
      />
      {shownError && (
        <p role="alert" className="text-sm text-negative">
          {shownError}
        </p>
      )}
    </div>
  )
}
