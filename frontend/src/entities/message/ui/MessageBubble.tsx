import { FileText, Info } from 'lucide-react'
import { formatDateTime, formatFileSize } from '@/shared/lib/format'
import { systemText } from '../lib/system-text'
import type { Message, MessageFile } from '../model/types'

function Attachment({ file }: { file: MessageFile }) {
  if (file.mime.startsWith('image/')) {
    return (
      <a href={file.url} target="_blank" rel="noreferrer" className="block">
        <img
          src={file.url}
          alt={file.original_name ?? 'Фото'}
          className="max-h-60 rounded-lg object-cover"
          loading="lazy"
        />
      </a>
    )
  }
  return (
    <a
      href={file.url}
      target="_blank"
      rel="noreferrer"
      className="flex items-center gap-2 rounded-lg bg-black/5 px-3 py-2 text-sm dark:bg-white/10"
    >
      <FileText size={20} strokeWidth={2} className="shrink-0" />
      <span className="min-w-0 truncate">{file.original_name ?? 'Файл'}</span>
      <span className="shrink-0 opacity-60">{formatFileSize(file.size)}</span>
    </a>
  )
}

export function MessageBubble({ message }: { message: Message }) {
  if (message.sender_type === 'SYSTEM') {
    return (
      <div className="mx-auto flex max-w-[85%] items-start gap-1.5 rounded-2xl bg-neutral-200/60 px-3 py-1.5 text-xs text-neutral-600 dark:bg-neutral-800/80 dark:text-neutral-300">
        <Info size={14} strokeWidth={2} className="mt-px shrink-0 opacity-70" />
        <span>{systemText(message.text)}</span>
      </div>
    )
  }

  const fromStaff = message.sender_type === 'STAFF'
  return (
    <div className={`flex ${fromStaff ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`flex max-w-[80%] flex-col gap-2 rounded-2xl px-3 py-2 ${
          fromStaff
            ? 'rounded-br-md bg-brand text-white'
            : 'rounded-bl-md bg-white shadow-sm dark:bg-neutral-800'
        }`}
      >
        {fromStaff && message.author && (
          <div className="text-xs font-medium opacity-80">{message.author.first_name}</div>
        )}
        {message.files.map((file) => (
          <Attachment key={file.id} file={file} />
        ))}
        {message.text && <p className="break-words whitespace-pre-wrap">{message.text}</p>}
        <div className="self-end text-[11px] opacity-60">{formatDateTime(message.created_at)}</div>
      </div>
    </div>
  )
}
