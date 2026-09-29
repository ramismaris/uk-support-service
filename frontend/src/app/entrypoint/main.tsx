import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '../styles/index.css'
import '../session/api-session'
import { paintTheme, readCachedTheme } from '@/entities/theme'
import { AppProviders } from './AppProviders'
import { showScrollbarsWhileScrolling } from './scrollbars'
import { reloadOnStaleBuild } from './stale-build'

// Last known company colour and name before the first paint; the real theme loads after sign-in.
paintTheme(readCachedTheme())
reloadOnStaleBuild()
showScrollbarsWhileScrolling()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProviders />
  </StrictMode>,
)
