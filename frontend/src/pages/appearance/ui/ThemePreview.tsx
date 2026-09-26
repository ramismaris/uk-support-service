import { MaxUI } from '@maxhub/max-ui'
import type { CSSProperties } from 'react'
import { animations, LottieAnimation } from '@/shared/ui/lottie'
import { brandInitials } from '@/widgets/app-shell'

interface ThemePreviewProps {
  companyName: string
  primaryColor: string
  logoUrl: string | null
}

type Scheme = 'light' | 'dark'

function MiniPanel({
  scheme,
  companyName,
  primaryColor,
  logoUrl,
}: ThemePreviewProps & { scheme: Scheme }) {
  const name = companyName.trim() || 'Название УК'
  return (
    // Its own Max UI root: the tokens follow this scheme, the accent follows the draft colour.
    <div data-color-scheme={scheme} style={{ '--brand': primaryColor } as CSSProperties}>
      <MaxUI
        colorScheme={scheme}
        className="app-font overflow-hidden rounded-2xl border border-line bg-layer text-fg"
      >
        <div className="flex items-center gap-2 border-b border-line px-3 py-2.5">
          {logoUrl ? (
            <img src={logoUrl} alt="" className="size-7 shrink-0 rounded-lg object-contain" />
          ) : (
            <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-brand text-xs font-semibold text-white">
              {brandInitials(name)}
            </span>
          )}
          <span className="truncate text-sm font-semibold">{name}</span>
        </div>
        <div className="flex items-center gap-2 bg-brand/10 px-3 py-2 text-xs">
          <span className="size-2 shrink-0 rounded-full bg-brand" />
          <span className="truncate">Не работает лифт во втором подъезде</span>
        </div>
        <div className="flex flex-col gap-2 bg-layer-2 p-3">
          <LottieAnimation
            src={animations.emptyChat}
            tint={primaryColor}
            className="mx-auto size-16"
          />
          <div className="flex justify-end">
            <div className="max-w-[85%] rounded-2xl rounded-br-md bg-brand px-3 py-1.5 text-xs text-white">
              Заявку взяли в работу, мастер придёт завтра
            </div>
          </div>
          <span className="self-start rounded-full bg-brand px-3 py-1.5 text-xs font-medium text-white">
            Взять в работу
          </span>
        </div>
      </MaxUI>
    </div>
  )
}

// How the panel will look in both of Max's colour schemes before the colour is saved.
export function ThemePreview(props: ThemePreviewProps) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-medium">Так увидят сотрудники</span>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
        <MiniPanel scheme="light" {...props} />
        <MiniPanel scheme="dark" {...props} />
      </div>
    </div>
  )
}
