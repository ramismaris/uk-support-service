import { useState } from 'react'
import { useBrandTheme } from '@/entities/theme'

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0))
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

// The company's logo, or its initials on the brand colour until a logo is uploaded.
export function BrandMark({ withName = false }: { withName?: boolean }) {
  const theme = useBrandTheme()
  const [broken, setBroken] = useState<string | null>(null)
  const showLogo = theme.logoUrl !== null && broken !== theme.logoUrl

  return (
    <div className="flex min-w-0 items-center gap-3" title={theme.companyName}>
      {showLogo ? (
        <img
          src={theme.logoUrl!}
          alt=""
          className="size-9 shrink-0 rounded-xl object-contain"
          onError={() => setBroken(theme.logoUrl)}
        />
      ) : (
        <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-brand text-sm font-semibold text-white">
          {initials(theme.companyName)}
        </span>
      )}
      {withName && <span className="truncate text-base font-semibold">{theme.companyName}</span>}
    </div>
  )
}
