import type { ReactNode } from 'react'

interface EmptyStateProps {
  icon: ReactNode
  title: string
  text?: string
  action?: ReactNode
  // Lottie animation; replaces the icon when given.
  animation?: ReactNode
}

export function EmptyState({ icon, title, text, action, animation }: EmptyStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
      <div className="flex size-32 items-center justify-center text-fg-3">{animation ?? icon}</div>
      <div className="font-medium">{title}</div>
      {text && <p className="max-w-xs text-sm text-fg-2">{text}</p>}
      {action}
    </div>
  )
}
