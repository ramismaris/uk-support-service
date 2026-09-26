import { QueryClientProvider } from '@tanstack/react-query'
import { MotionConfig } from 'framer-motion'
import { RouterProvider } from 'react-router'
import { queryClient } from '@/shared/api'
import { router } from '../routes/router'
import { BrandTheme } from '../theme/BrandTheme'
import { ThemeProvider } from '../theme/ThemeProvider'

export function AppProviders() {
  return (
    <ThemeProvider>
      <MotionConfig reducedMotion="user">
        <QueryClientProvider client={queryClient}>
          <BrandTheme />
          <RouterProvider router={router} />
        </QueryClientProvider>
      </MotionConfig>
    </ThemeProvider>
  )
}
