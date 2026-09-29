import { useBrandTheme } from '@/entities/theme'
import { BrandLogo } from './BrandLogo'

export function BrandMark({ withName = false }: { withName?: boolean }) {
  const theme = useBrandTheme()

  return (
    <div className="flex min-w-0 items-center gap-3" title={theme.companyName}>
      <BrandLogo theme={theme} />
      {withName && <span className="truncate text-base font-semibold">{theme.companyName}</span>}
    </div>
  )
}
