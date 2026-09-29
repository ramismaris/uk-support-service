import { ExternalLink } from 'lucide-react'
import { MaxText } from '@/shared/ui/max-text'

export interface BotMessageButton {
  label: string
  url?: string | null
}

interface BotMessageProps {
  text: string
  photoUrl?: string | null
  buttons?: BotMessageButton[]
  // Shown in grey while the text is still empty.
  placeholder: string
  buttonPlaceholder?: string
}

export function BotMessage({
  text,
  photoUrl,
  buttons = [],
  placeholder,
  buttonPlaceholder = 'Текст кнопки',
}: BotMessageProps) {
  return (
    <div className="flex max-w-80 flex-col gap-1">
      <div className="overflow-hidden rounded-2xl rounded-bl-md bg-layer">
        {photoUrl && <img src={photoUrl} alt="" className="max-h-48 w-full object-cover" />}
        {text.trim() ? (
          <MaxText text={text} className="px-3 py-2 text-[15px] leading-5 [&_a]:text-brand" />
        ) : (
          <p className="px-3 py-2 text-[15px] leading-5 text-fg-3">{placeholder}</p>
        )}
      </div>
      {buttons.map((button, index) => (
        <span
          key={`${button.label}-${index}`}
          className="flex items-center justify-center gap-1.5 rounded-xl bg-layer/70 px-3 py-2 text-sm font-medium text-brand"
        >
          {button.label.trim() || buttonPlaceholder}
          {button.url && <ExternalLink size={14} strokeWidth={2} />}
        </span>
      ))}
    </div>
  )
}
