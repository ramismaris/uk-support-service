import { lazy, Suspense } from 'react'
import type { RichTextFieldProps } from './RichTextField'

const Editor = lazy(() =>
  import('./RichTextField').then((module) => ({ default: module.RichTextField })),
)

export function RichTextField(props: RichTextFieldProps) {
  return (
    <Suspense fallback={<div className="h-52 animate-pulse rounded-xl bg-fill" />}>
      <Editor {...props} />
    </Suspense>
  )
}
