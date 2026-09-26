import { ExternalLink } from 'lucide-react'
import type { BotPreview as Preview } from '../lib/preview'

// How the resident sees the section in Max: a bot message with inline buttons under it.
export function BotPreview({ preview, section }: { preview: Preview; section: string }) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs font-medium text-fg-3">Так увидит жилец</span>
      <div className="rounded-2xl bg-surface p-4">
        <div className="flex max-w-80 flex-col gap-1">
          <div className="overflow-hidden rounded-2xl rounded-bl-md bg-layer">
            {preview.photoUrl && (
              <img src={preview.photoUrl} alt="" className="max-h-48 w-full object-cover" />
            )}
            <p
              className={`px-3 py-2 text-[15px] leading-5 whitespace-pre-wrap ${
                preview.text.trim() ? '' : 'text-fg-3'
              }`}
            >
              {preview.text.trim() ? preview.text : `Текст раздела «${section}»`}
            </p>
          </div>
          {preview.buttons.map((button, index) => (
            <span
              key={`${button.label}-${index}`}
              className="flex items-center justify-center gap-1.5 rounded-xl bg-layer/70 px-3 py-2 text-sm font-medium text-brand"
            >
              {button.label.trim() || 'Текст кнопки'}
              {button.url && <ExternalLink size={14} strokeWidth={2} />}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
