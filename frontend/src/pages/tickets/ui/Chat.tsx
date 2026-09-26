import { Button } from '@maxhub/max-ui'
import { AnimatePresence, motion } from 'framer-motion'
import { MessageCircle } from 'lucide-react'
import { useEffect, useLayoutEffect, useRef } from 'react'
import { MessageBubble, useMessages } from '@/entities/message'
import type { TicketDetail } from '@/entities/ticket'
import { EmptyState } from '@/shared/ui/empty-state'
import { animations, LottieAnimation } from '@/shared/ui/lottie'
import { useMarkRead } from '../model/use-mark-read'
import { Composer } from './Composer'

const NEAR_BOTTOM = 80

export function Chat({ ticket }: { ticket: TicketDetail }) {
  const messages = useMessages(ticket.id)
  const markRead = useMarkRead(ticket.id)
  const scroller = useRef<HTMLDivElement>(null)
  const stickToBottom = useRef(true)
  const items = messages.data ?? []
  const lastClientMessageId = items.findLast((m) => m.sender_type === 'CLIENT')?.id

  // The chat is on screen: mark it read when it opens and when the client writes again.
  useEffect(() => {
    markRead()
  }, [ticket.id, lastClientMessageId, markRead])

  useLayoutEffect(() => {
    const element = scroller.current
    if (element && stickToBottom.current) {
      element.scrollTop = element.scrollHeight
    }
  }, [items.length, ticket.id])

  const closed = ticket.status === 'CLOSED' || ticket.status === 'REJECTED'

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div
        ref={scroller}
        className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto bg-neutral-50 p-4 dark:bg-neutral-950"
        onScroll={(event) => {
          const element = event.currentTarget
          stickToBottom.current =
            element.scrollHeight - element.scrollTop - element.clientHeight < NEAR_BOTTOM
        }}
      >
        {messages.isPending && <div className="m-auto text-sm text-neutral-500">Загрузка…</div>}
        {messages.isError && (
          <EmptyState
            icon={<MessageCircle size={48} strokeWidth={1.5} />}
            title="Не удалось загрузить переписку"
            text={messages.error.message}
            action={<Button onClick={() => void messages.refetch()}>Повторить</Button>}
          />
        )}
        {messages.isSuccess && items.length === 0 && (
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
        <AnimatePresence initial={false}>
          {items.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              <MessageBubble message={message} />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
      {closed ? (
        <div className="border-t border-neutral-200 p-4 text-center text-sm text-neutral-500 dark:border-neutral-800">
          Обращение закрыто — писать в него нельзя
        </div>
      ) : (
        <Composer ticketId={ticket.id} />
      )}
    </div>
  )
}
