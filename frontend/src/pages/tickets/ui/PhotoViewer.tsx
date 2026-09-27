import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { ChevronLeft, ChevronRight, Download, X } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { formatDateTime } from '@/shared/lib/format'
import type { ChatPhoto } from '../lib/chat-photos'
import { stepIndex, swipeAction } from '../lib/photo-viewer'

const iconButton =
  'flex size-10 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/10 hover:text-white'

export function PhotoViewer({
  photos,
  index,
  onIndexChange,
  onClose,
}: {
  photos: ChatPhoto[]
  index: number
  onIndexChange: (index: number) => void
  onClose: () => void
}) {
  const reduced = useReducedMotion() ?? false
  const closeButton = useRef<HTMLButtonElement>(null)
  const photo = photos[index]!
  const step = (delta: number) => onIndexChange(stepIndex(index, delta, photos.length))

  // Focus moves into the viewer and returns to the photo it was opened from.
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null
    closeButton.current?.focus()
    return () => opener?.focus()
  }, [])

  useEffect(() => {
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      } else if (event.key === 'ArrowLeft') {
        onIndexChange(stepIndex(index, -1, photos.length))
      } else if (event.key === 'ArrowRight') {
        onIndexChange(stepIndex(index, 1, photos.length))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [index, photos.length, onIndexChange, onClose])

  // Warm up the neighbours so flipping does not wait for the network.
  useEffect(() => {
    for (const neighbour of [photos[index - 1], photos[index + 1]]) {
      if (neighbour) {
        new Image().src = neighbour.file.url
      }
    }
  }, [index, photos])

  return createPortal(
    <motion.div
      role="dialog"
      aria-modal="true"
      aria-label="Просмотр фото"
      className="fixed inset-0 z-[60] flex flex-col bg-black/95 text-white select-none"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: reduced ? 0 : 0.15 }}
    >
      <div className="flex items-center gap-2 px-2 py-2">
        <span className="flex-1 px-2 text-sm text-white/80">
          {photos.length > 1 ? `${index + 1} из ${photos.length}` : 'Фото'}
        </span>
        <a
          href={photo.file.url}
          download={photo.file.original_name ?? true}
          aria-label="Скачать"
          className={iconButton}
        >
          <Download size={20} strokeWidth={2} />
        </a>
        <button
          ref={closeButton}
          type="button"
          aria-label="Закрыть"
          className={iconButton}
          onClick={onClose}
        >
          <X size={22} strokeWidth={2} />
        </button>
      </div>

      <div
        className="relative flex min-h-0 flex-1 items-center justify-center overflow-hidden"
        // A click on the dark area around the photo closes the viewer.
        onClick={(event) => event.target === event.currentTarget && onClose()}
      >
        <AnimatePresence initial={false} mode="popLayout">
          <motion.img
            key={photo.file.id}
            src={photo.file.url}
            alt={photo.file.original_name ?? 'Фото'}
            draggable={false}
            className="max-h-full max-w-full touch-none object-contain"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reduced ? 0 : 0.15 }}
            drag
            dragSnapToOrigin
            dragElastic={0.6}
            onDragEnd={(_, info) => {
              const action = swipeAction(info.offset)
              if (action === 'close') {
                onClose()
              } else if (action) {
                step(action === 'next' ? 1 : -1)
              }
            }}
          />
        </AnimatePresence>
        {index > 0 && (
          <button
            type="button"
            aria-label="Предыдущее фото"
            className={`${iconButton} absolute left-3 bg-black/30 pointer-coarse:hidden`}
            onClick={() => step(-1)}
          >
            <ChevronLeft size={24} strokeWidth={2} />
          </button>
        )}
        {index < photos.length - 1 && (
          <button
            type="button"
            aria-label="Следующее фото"
            className={`${iconButton} absolute right-3 bg-black/30 pointer-coarse:hidden`}
            onClick={() => step(1)}
          >
            <ChevronRight size={24} strokeWidth={2} />
          </button>
        )}
      </div>

      <p className="px-4 py-3 text-center text-sm text-white/80">
        {photo.author} · {formatDateTime(photo.sentAt)}
      </p>
    </motion.div>,
    document.body,
  )
}
