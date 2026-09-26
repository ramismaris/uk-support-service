import { LoaderCircle, Paperclip, SendHorizontal, X } from 'lucide-react'
import { useLayoutEffect, useRef, useState, type KeyboardEvent } from 'react'
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
  const textArea = useRef<HTMLTextAreaElement>(null)
  const send = useSendMessage(ticketId)

  // Grow with the text up to max-h, then scroll.
  useLayoutEffect(() => {
    const element = textArea.current
    if (element) {
      element.style.height = 'auto'
      element.style.height = `${element.scrollHeight}px`
    }
  }, [text])

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
    <div className="flex flex-col gap-2 border-t border-line px-3 py-2">
      {files.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {files.map((file, index) => (
            <li
              key={`${file.name}-${index}`}
              className="flex items-center gap-1 rounded-full bg-fill py-1 pr-1 pl-3 text-xs"
            >
              <span className="max-w-40 truncate">{file.name}</span>
              <span className="text-fg-3">{formatFileSize(file.size)}</span>
              <button
                type="button"
                aria-label={`Убрать ${file.name}`}
                className="rounded-full p-1 hover:bg-press"
                onClick={() => setFiles(files.filter((_, i) => i !== index))}
              >
                <X size={12} strokeWidth={2} />
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex items-end gap-1 rounded-3xl bg-fill p-1">
        <button
          type="button"
          aria-label="Прикрепить файлы"
          disabled={send.isPending}
          className="flex size-9 shrink-0 items-center justify-center rounded-full text-fg-3 transition-colors hover:bg-press hover:text-fg"
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
        <textarea
          ref={textArea}
          value={text}
          rows={1}
          maxLength={MESSAGE_TEXT_LIMIT + 1}
          placeholder="Ответ жильцу"
          disabled={send.isPending}
          className="max-h-36 min-h-9 min-w-0 flex-1 resize-none bg-transparent px-1 py-2 text-[15px] leading-5 outline-none placeholder:text-fg-3"
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
        />
        <button
          type="button"
          aria-label="Отправить"
          disabled={!canSend}
          onClick={submit}
          className={`flex size-9 shrink-0 items-center justify-center rounded-full transition-colors ${
            canSend || showSent ? 'bg-brand text-white hover:brightness-110' : 'text-fg-3'
          }`}
        >
          {showSent ? (
            <LottieAnimation
              key={sentCount}
              src={animations.sent}
              speed={3.3}
              className="-m-1.5 size-12"
              onComplete={() => setShowSent(false)}
            />
          ) : send.isPending ? (
            <LoaderCircle size={18} strokeWidth={2} className="animate-spin" />
          ) : (
            <SendHorizontal size={18} strokeWidth={2} />
          )}
        </button>
      </div>
      {error && (
        <p role="alert" className="text-sm text-negative">
          {error}
        </p>
      )}
    </div>
  )
}
