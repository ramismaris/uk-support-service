import { FileText } from 'lucide-react'
import { formatDateTime, formatFileSize } from '@/shared/lib/format'
import { isPhoto } from '../lib/photo'
import { systemText } from '../lib/system-text'
import type { Message, MessageFile } from '../model/types'
import { PhotoAlbum } from './PhotoAlbum'

function Document({ file }: { file: MessageFile }) {
  return (
    <a
      href={file.url}
      target="_blank"
      rel="noreferrer"
      className="flex items-center gap-2 rounded-lg bg-fill px-3 py-2 text-sm"
    >
      <FileText size={20} strokeWidth={2} className="shrink-0" />
      <span className="min-w-0 truncate">{file.original_name ?? 'Файл'}</span>
      <span className="shrink-0 opacity-60">{formatFileSize(file.size)}</span>
    </a>
  )
}

export function MessageBubble({
  message,
  onOpenPhoto,
}: {
  message: Message
  onOpenPhoto?: (fileId: number) => void
}) {
  if (message.sender_type === 'SYSTEM') {
    return (
      // Quiet line, not a bubble: it is what the bot told the resident, not part of the dialogue.
      <p className="mx-auto max-w-[85%] py-0.5 text-center text-xs leading-4 text-fg-3">
        Бот → жильцу: {systemText(message.text)} · {formatDateTime(message.created_at)}
      </p>
    )
  }

  const fromStaff = message.sender_type === 'STAFF'
  const photos = message.files.filter(isPhoto)
  const documents = message.files.filter((file) => !isPhoto(file))
  const time = formatDateTime(message.created_at)
  // Like Telegram: a photo without a caption carries its time on top of the picture.
  const timeOverPhoto = photos.length > 0 && documents.length === 0 && !message.text

  return (
    <div className={`flex ${fromStaff ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`flex max-w-[80%] flex-col overflow-hidden rounded-2xl ${
          photos.length > 0 ? 'w-80' : ''
        } ${fromStaff ? 'rounded-br-md bg-brand text-white' : 'rounded-bl-md bg-layer'}`}
      >
        {fromStaff && message.author && (
          <div className="px-3 pt-2 pb-1 text-xs font-medium opacity-80">
            {message.author.first_name}
          </div>
        )}
        {photos.length > 0 && (
          <div className="relative">
            <PhotoAlbum photos={photos} onOpen={onOpenPhoto} />
            {timeOverPhoto && (
              <span className="pointer-events-none absolute right-1.5 bottom-1.5 rounded-full bg-black/45 px-2 py-0.5 text-[11px] text-white">
                {time}
              </span>
            )}
          </div>
        )}
        {!timeOverPhoto && (
          <div className="flex flex-col gap-2 px-3 py-2">
            {documents.map((file) => (
              <Document key={file.id} file={file} />
            ))}
            {message.text && <p className="break-words whitespace-pre-wrap">{message.text}</p>}
            <div className="self-end text-[11px] opacity-60">{time}</div>
          </div>
        )}
      </div>
    </div>
  )
}
