import { Typography } from '@maxhub/max-ui'
import type { ReactNode } from 'react'
import { PageTransition } from '../page-transition'

interface StatusScreenProps {
  title: string
  text: string
  action?: ReactNode
}

export function StatusScreen({ title, text, action }: StatusScreenProps) {
  return (
    <div className="flex min-h-dvh items-center justify-center p-4">
      <PageTransition className="flex max-w-sm flex-col items-center gap-3 text-center">
        <Typography.Title>{title}</Typography.Title>
        <p className="text-neutral-500 dark:text-neutral-400">{text}</p>
        {action && <div className="mt-2">{action}</div>}
      </PageTransition>
    </div>
  )
}
