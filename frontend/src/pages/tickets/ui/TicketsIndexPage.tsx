import { MessagesSquare } from 'lucide-react'
import { EmptyState } from '@/shared/ui/empty-state'

export function TicketsIndexPage() {
  return (
    <EmptyState
      icon={<MessagesSquare size={48} strokeWidth={1.5} />}
      title="Выберите обращение"
      text="Слева — активные обращения жильцов. Новые появляются автоматически."
    />
  )
}
