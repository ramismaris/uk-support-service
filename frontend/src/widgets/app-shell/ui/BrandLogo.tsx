import { useState } from 'react'
import type { BrandTheme } from '@/entities/theme'
import { brandInitials } from '../model/brand'

const SIZES = {
  md: 'size-9 rounded-xl text-sm',
  xl: 'size-20 rounded-3xl text-3xl',
} as const

// The company's logo, or its initials on the brand colour until a logo is uploaded.
export function BrandLogo({
  theme,
  size = 'md',
}: {
  theme: BrandTheme
  size?: keyof typeof SIZES
}) {
  const [broken, setBroken] = useState<string | null>(null)
  const showLogo = theme.logoUrl !== null && broken !== theme.logoUrl

  if (showLogo) {
    return (
      <img
        src={theme.logoUrl!}
        alt=""
        className={`${SIZES[size]} shrink-0 object-contain`}
        onError={() => setBroken(theme.logoUrl)}
      />
    )
  }
  return (
    <span
      className={`${SIZES[size]} flex shrink-0 items-center justify-center bg-brand font-semibold text-white`}
    >
      {brandInitials(theme.companyName)}
    </span>
  )
}
