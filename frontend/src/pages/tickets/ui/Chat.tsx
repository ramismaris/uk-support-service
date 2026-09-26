import { Button } from '@maxhub/max-ui'
import { AnimatePresence, motion } from 'framer-motion'
import { MessageCircle } from 'lucide-react'
import { useEffect, useLayoutEffect, useMemo, useRef } from 'react'
import { MessageBubble, useMessages } from '@/entities/message'
import type { TicketDetail } from '@/entities/ticket'
import { formatDateTime } from '@/shared/lib/format'
import { EmptyState } from '@/shared/ui/empty-state'
import { animations, LottieAnimation } from '@/shared/ui/lottie'
import { buildTimeline, type TimelineItem } from '../lib/timeline'
import { useMarkRead } from '../model/use-mark-read'
import { Composer } from './Composer'

const NEAR_BOTTOM = 80

function TimelineEvent({ item }: { item: Extract<TimelineItem, { kind: 'event' }> }) {
  return (
    <p className="py-0.5 text-center text-xs leading-4 text-fg-3">
      {item.actor && <span className="text-fg-2">{item.actor} · </span>}
      {item.text}
      {item.comment && <span className="text-fg-2"> «{item.comment}»</span>} ·{' '}
      {formatDateTime(item.at)}
    </p>
  )
}

function closedNotice(status: TicketDetail['status']): string | null {
  if (status === 'CLOSED') {
    return 'Обращение закрыто — писать в него нельзя'
  }
  if (status === 'REJECTED') {
    return 'Обращение отклонено — писать в него нельзя'
  }
  return null
}

export function Chat({ ticket }: { ticket: TicketDetail }) {
  const messages = useMessages(ticket.id)
  const markRead = useMarkRead(ticket.id)
  const scroller = useRef<HTMLDivElement>(null)
  const stickToBottom = useRef(true)
  const list = useMemo(() => messages.data ?? [], [messages.data])
  const timeline = useMemo(() => buildTimeline(list, ticket.history), [list, ticket.history])
  const lastClientMessageId = list.findLast((m) => m.sender_type === 'CLIENT')?.id

  // The chat is on screen: mark it read when it opens and when the resident writes again.
  useEffect(() => {
    markRead()
  }, [ticket.id, lastClientMessageId, markRead])

  useLayoutEffect(() => {
    const element = scroller.current
    if (element && stickToBottom.current) {
      element.scrollTop = element.scrollHeight
    }
  }, [timeline.length, ticket.id])

  const notice = closedNotice(ticket.status)

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div
        ref={scroller}
        className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto bg-surface px-4 py-3"
        onScroll={(event) => {
          const element = event.currentTarget
          stickToBottom.current =
            element.scrollHeight - element.scrollTop - element.clientHeight < NEAR_BOTTOM
        }}
      >
        {messages.isPending && <div className="m-auto text-sm text-fg-3">Загрузка…</div>}
        {messages.isError && (
          <EmptyState
            icon={<MessageCircle size={48} strokeWidth={1.5} />}
            title="Не удалось загрузить переписку"
            text={messages.error.message}
            action={<Button onClick={() => void messages.refetch()}>Повторить</Button>}
          />
        )}
        {messages.isSuccess && (
          <AnimatePresence initial={false}>
            {timeline.map((item) => (
              <motion.div
                key={item.key}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
              >
                {item.kind === 'message' ? (
                  <MessageBubble message={item.message} />
                ) : (
                  <TimelineEvent item={item} />
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        )}
        {messages.isSuccess && list.length === 0 && (
          <EmptyState
            icon={<MessageCircle size={48} strokeWidth={1.5} />}
            title="Сообщений пока нет"
            text="Напишите жильцу — ответ придёт ему в Max."
            animation={
              <LottieAnimation
                src={animations.emptyChat}
                speed={0.7}
                repeatDelay={1500}
                className="size-32"
              />
            }
          />
        )}
      </div>
      {notice ? (
        <div className="border-t border-line p-4 text-center text-sm text-fg-3">{notice}</div>
      ) : (
        <Composer ticketId={ticket.id} />
      )}
    </div>
  )
}
