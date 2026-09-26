import { IconButton, Textarea } from '@maxhub/max-ui'
import { Paperclip, SendHorizontal, X } from 'lucide-react'
import { useRef, useState, type KeyboardEvent } from 'react'
import { formatFileSize } from '@/shared/lib/format'
import { animations, LottieAnimation } from '@/shared/ui/lottie'
import { hasContent, MESSAGE_TEXT_LIMIT, validateMessage } from '../lib/message-rules'
import { useSendMessage } from '../model/use-send-message'

export function Composer({ ticketId }: { ticketId: number }) {
  const [text, setText] = useState('')
  const [files, setFiles] = useState<File[]>([])
  // Bumped on every successful send to replay the "sent" check inside the button.
  const [sentCount, setSentCount] = useState(0)
  const [showSent, setShowSent] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)
  const send = useSendMessage(ticketId)

  const validationError = validateMessage(text, files)
  const canSend = hasContent(text, files) && validationError === null && !send.isPending

  const submit = () => {
    if (!canSend) {
      return
    }
    send.mutate(
      { text, files },
      {
        onSuccess: () => {
          setText('')
          setFiles([])
          setSentCount((count) => count + 1)
          setShowSent(true)
        },
      },
    )
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  const error = validationError ?? send.error?.message

  return (
    <div className="flex flex-col gap-2 border-t border-neutral-200 p-3 dark:border-neutral-800">
      {files.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {files.map((file, index) => (
            <li
              key={`${file.name}-${index}`}
              className="flex items-center gap-1 rounded-full bg-neutral-100 py-1 pr-1 pl-3 text-xs dark:bg-neutral-800"
            >
              <span className="max-w-40 truncate">{file.name}</span>
              <span className="text-neutral-500">{formatFileSize(file.size)}</span>
              <button
                type="button"
                aria-label={`Убрать ${file.name}`}
                className="rounded-full p-1 hover:bg-neutral-200 dark:hover:bg-neutral-700"
                onClick={() => setFiles(files.filter((_, i) => i !== index))}
              >
                <X size={12} strokeWidth={2} />
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex items-end gap-2">
        <button
          type="button"
          aria-label="Прикрепить файлы"
          disabled={send.isPending}
          className="rounded-full p-2 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800"
          onClick={() => fileInput.current?.click()}
        >
          <Paperclip size={20} strokeWidth={2} />
        </button>
        <input
          ref={fileInput}
          type="file"
          multiple
          hidden
          onChange={(event) => {
            setFiles([...files, ...Array.from(event.target.files ?? [])])
            event.target.value = ''
          }}
        />
        <Textarea
          value={text}
          rows={1}
          maxLength={MESSAGE_TEXT_LIMIT + 1}
          placeholder="Сообщение"
          disabled={send.isPending}
          className="max-h-40 min-w-0 flex-1 resize-none"
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
        />
        <IconButton
          aria-label="Отправить"
          size="large"
          variant={canSend || showSent ? 'primary' : 'secondary'}
          disabled={!canSend && !showSent}
          loading={send.isPending}
          onClick={submit}
          className="shrink-0 rounded-full"
        >
          {showSent ? (
            <LottieAnimation
              key={sentCount}
              src={animations.sent}
              speed={3.3}
              className="-m-3 size-12"
              onComplete={() => setShowSent(false)}
            />
          ) : (
            <SendHorizontal size={20} strokeWidth={2} />
          )}
        </IconButton>
      </div>
      {error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  )
}
