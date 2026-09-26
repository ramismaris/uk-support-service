import { MessagesSquare } from 'lucide-react'
import { EmptyState } from '@/shared/ui/empty-state'
import { animations, LottieAnimation } from '@/shared/ui/lottie'

export function TicketsIndexPage() {
  return (
    <EmptyState
      icon={<MessagesSquare size={48} strokeWidth={1.5} />}
      title="Выберите обращение"
      text="Слева — активные обращения жильцов. Новые появляются автоматически."
      animation={
        <LottieAnimation
          src={animations.selectTicket}
          speed={0.7}
          repeatDelay={1500}
          className="size-32"
        />
      }
    />
  )
}
