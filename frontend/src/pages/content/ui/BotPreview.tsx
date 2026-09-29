import { BotMessage } from '@/shared/ui/bot-message'
import type { BotPreview as Preview } from '../lib/preview'

export function BotPreview({ preview, section }: { preview: Preview; section: string }) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs font-medium text-fg-3">Так увидит жилец</span>
      <div className="rounded-2xl bg-surface p-4">
        <BotMessage
          text={preview.text}
          photoUrl={preview.photoUrl}
          buttons={preview.buttons}
          placeholder={`Текст раздела «${section}»`}
        />
      </div>
    </div>
  )
}
