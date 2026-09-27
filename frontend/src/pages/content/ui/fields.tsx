import { lazy, Suspense, type ReactNode } from 'react'

// The editor (TipTap) is heavy and only admins open it: its own chunk, loaded on demand.
const RichTextField = lazy(() =>
  import('./RichTextField').then((module) => ({ default: module.RichTextField })),
)

const control =
  'w-full rounded-xl bg-fill px-3 py-2.5 text-[15px] leading-5 outline-none placeholder:text-fg-3 focus:ring-2 focus:ring-brand/40'

function Field({
  label,
  counter,
  error,
  children,
}: {
  label: string
  counter?: string
  error?: string
  children: ReactNode
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="flex items-baseline justify-between gap-2 text-sm">
        <span className="font-medium">{label}</span>
        {counter && <span className="text-xs text-fg-3">{counter}</span>}
      </span>
      {children}
      {error && <span className="text-sm text-negative">{error}</span>}
    </label>
  )
}

interface TextFieldProps {
  label: string
  value: string
  limit: number
  onChange: (value: string) => void
  error?: string
  multiline?: boolean
  // A formatting editor for texts the bot sends as Max markdown.
  formatting?: boolean
  placeholder?: string
}

export function TextField({
  label,
  value,
  limit,
  onChange,
  error,
  multiline = false,
  formatting = false,
  placeholder,
}: TextFieldProps) {
  if (formatting) {
    return (
      <Suspense fallback={<div className="h-52 animate-pulse rounded-xl bg-fill" />}>
        <RichTextField
          label={label}
          value={value}
          limit={limit}
          error={error}
          onChange={onChange}
        />
      </Suspense>
    )
  }
  return (
    <Field label={label} counter={`${value.length}/${limit}`} error={error}>
      {multiline ? (
        <textarea
          value={value}
          rows={6}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          className={`${control} resize-y`}
        />
      ) : (
        <input
          value={value}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          className={control}
        />
      )}
    </Field>
  )
}
