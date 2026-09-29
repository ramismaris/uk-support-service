import { Button } from '@maxhub/max-ui'
import { AnimatePresence, motion } from 'framer-motion'
import { MessageCircle } from 'lucide-react'
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { MessageBubble, useMessages } from '@/entities/message'
import type { TicketDetail } from '@/entities/ticket'
import { formatDayLabel, formatTime } from '@/shared/lib/format'
import { useBrandColor } from '@/entities/theme'
import { EmptyState } from '@/shared/ui/empty-state'
import { animations, LottieAnimation } from '@/shared/ui/lottie'
import { floatingDayIndex, groupByDay } from '../lib/chat-days'
import { chatPhotos } from '../lib/chat-photos'
import { buildTimeline, type TimelineItem } from '../lib/timeline'
import { firstUnreadMessageId } from '../lib/unread-divider'
import { useMarkRead } from '../model/use-mark-read'
import { Composer } from './Composer'
import { PhotoViewer } from './PhotoViewer'

const NEAR_BOTTOM = 80
// The floating date hides this long after scrolling stops, as in Telegram.
const FLOATING_DATE_MS = 1000
// Pill height: its separator counts as gone once it slides under the floating one.
const SEPARATOR_OFFSET = 8

function TimelineEvent({ item }: { item: Extract<TimelineItem, { kind: 'event' }> }) {
  return (
    <p className="py-0.5 text-center text-xs leading-4 text-fg-3">
      {item.actor && <span className="text-fg-2">{item.actor} · </span>}
      {item.text}
      {item.comment && <span className="text-fg-2"> «{item.comment}»</span>} · {formatTime(item.at)}
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
  const days = useMemo(() => groupByDay(timeline), [timeline])
  const [floatingDate, setFloatingDate] = useState<string | null>(null)
  const floatingTimer = useRef<number | undefined>(undefined)

  const showFloatingDate = (element: HTMLElement) => {
    const separators = element.querySelectorAll<HTMLElement>('[data-day-separator]')
    const tops = Array.from(separators, (separator) => separator.offsetTop)
    const index = floatingDayIndex(tops, element.scrollTop + SEPARATOR_OFFSET)
    setFloatingDate(index === null ? null : (separators[index]?.dataset.daySeparator ?? null))
    window.clearTimeout(floatingTimer.current)
    floatingTimer.current = window.setTimeout(() => setFloatingDate(null), FLOATING_DATE_MS)
  }

  useEffect(() => () => window.clearTimeout(floatingTimer.current), [])
  // Our own jumps to the latest message are not the user scrolling: no floating date for them.
  const ownScroll = useRef(false)
  const pinToBottom = (element: HTMLElement) => {
    if (element.scrollTop !== element.scrollHeight - element.clientHeight) {
      ownScroll.current = true
      element.scrollTop = element.scrollHeight
    }
  }
  const residentName = [ticket.client.first_name, ticket.client.last_name].filter(Boolean).join(' ')
  const photos = useMemo(() => chatPhotos(list, residentName), [list, residentName])
  const [viewerIndex, setViewerIndex] = useState<number | null>(null)
  const openPhoto = (fileId: number) =>
    setViewerIndex(photos.findIndex((photo) => photo.file.id === fileId))
  // Fixed when the chat opens: opening marks it read, and the divider must not jump away.
  const [unreadFrom, setUnreadFrom] = useState<number | null | undefined>(undefined)
  if (unreadFrom === undefined && messages.isSuccess) {
    setUnreadFrom(firstUnreadMessageId(list, ticket.unread))
  }
  const lastClientMessageId = list.findLast((m) => m.sender_type === 'CLIENT')?.id

  // The chat is on screen: mark it read when it opens and when the resident writes again.
  useEffect(() => {
    markRead()
  }, [ticket.id, lastClientMessageId, markRead])

  useLayoutEffect(() => {
    const element = scroller.current
    if (element && stickToBottom.current) {
      pinToBottom(element)
    }
  }, [timeline.length, ticket.id])

  const notice = closedNotice(ticket.status)
  const brandColor = useBrandColor()

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      {/* Like Telegram: while scrolling, the day at the top shows here, then fades away. */}
      <AnimatePresence>
        {floatingDate && (
          <motion.div
            key="floating-date"
            className="pointer-events-none absolute inset-x-0 top-3 z-10 flex justify-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            <span className="rounded-full bg-black/35 px-3 py-1 text-xs font-medium text-white backdrop-blur-sm">
              {floatingDate}
            </span>
          </motion.div>
        )}
      </AnimatePresence>
      <div
        ref={scroller}
        className="relative flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto bg-surface px-4 py-3"
        // Photos get their height only once loaded; keep the chat pinned to the bottom meanwhile.
        onLoadCapture={() => {
          const element = scroller.current
          if (element && stickToBottom.current) {
            pinToBottom(element)
          }
        }}
        onScroll={(event) => {
          const element = event.currentTarget
          stickToBottom.current =
            element.scrollHeight - element.scrollTop - element.clientHeight < NEAR_BOTTOM
          if (ownScroll.current) {
            ownScroll.current = false
          } else {
            showFloatingDate(element)
          }
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
          // Like messengers: a short chat sits at the bottom, next to the composer.
          // With no messages yet the empty state stays in the middle instead.
          <div className={`flex flex-col gap-2 ${list.length > 0 ? 'mt-auto' : ''}`}>
            {days.map((day) => (
              <section key={day.key} className="flex flex-col gap-2">
                <div
                  data-day-separator={formatDayLabel(day.at)}
                  className="flex justify-center py-1"
                >
                  <span className="rounded-full bg-black/35 px-3 py-1 text-xs font-medium text-white backdrop-blur-sm">
                    {formatDayLabel(day.at)}
                  </span>
                </div>
                <AnimatePresence initial={false}>
                  {day.items.map((item) => (
                    <motion.div
                      key={item.key}
                      // Like Max on wide screens: the background spans the pane, messages keep a column.
                      className="mx-auto w-full max-w-3xl"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2, ease: 'easeOut' }}
                    >
                      {item.kind === 'message' && item.message.id === unreadFrom && (
                        <div className="flex items-center gap-3 py-2 text-xs font-medium text-brand">
                          <span className="h-px flex-1 bg-brand/30" />
                          Новые сообщения
                          <span className="h-px flex-1 bg-brand/30" />
                        </div>
                      )}
                      {item.kind === 'message' ? (
                        <MessageBubble message={item.message} onOpenPhoto={openPhoto} />
                      ) : (
                        <TimelineEvent item={item} />
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </section>
            ))}
          </div>
        )}
        {messages.isSuccess && list.length === 0 && (
          <EmptyState
            icon={<MessageCircle size={48} strokeWidth={1.5} />}
            title="Сообщений пока нет"
            text="Напишите жильцу — ответ придёт ему в Max."
            animation={
              <LottieAnimation
                src={animations.emptyChat}
                tint={brandColor}
                speed={0.7}
                className="size-32"
              />
            }
          />
        )}
      </div>
      <AnimatePresence>
        {viewerIndex !== null && (
          <PhotoViewer
            photos={photos}
            index={viewerIndex}
            onIndexChange={setViewerIndex}
            onClose={() => setViewerIndex(null)}
          />
        )}
      </AnimatePresence>
      {notice ? (
        <div className="border-t border-line p-4 text-center text-sm text-fg-3">{notice}</div>
      ) : (
        <Composer key={ticket.id} ticketId={ticket.id} />
      )}
    </div>
  )
}
