import { History } from 'lucide-react'

export function DraftNotice({ onReset }: { onReset: () => void }) {
  return (
    <p className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl bg-brand/10 px-3 py-2 text-sm">
      <History size={16} strokeWidth={2} aria-hidden="true" className="shrink-0 text-brand" />
      <span>Восстановили несохранённый черновик</span>
      <button
        type="button"
        onClick={onReset}
        className="ml-auto font-medium text-brand hover:underline"
      >
        Сбросить
      </button>
    </p>
  )
}
