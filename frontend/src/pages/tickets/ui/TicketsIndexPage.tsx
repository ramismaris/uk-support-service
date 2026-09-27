import { MessagesSquare } from 'lucide-react'
import { useBrandColor } from '@/entities/theme'
import { EmptyState } from '@/shared/ui/empty-state'
import { animations, LottieAnimation } from '@/shared/ui/lottie'

export function TicketsIndexPage() {
  const brandColor = useBrandColor()
  return (
    <EmptyState
      icon={<MessagesSquare size={48} strokeWidth={1.5} />}
      title="Выберите обращение"
      text="Слева — активные обращения жильцов. Новые появляются автоматически."
      animation={
        <LottieAnimation
          src={animations.selectTicket}
          tint={brandColor}
          speed={0.7}
          className="size-32"
        />
      }
    />
  )
}
