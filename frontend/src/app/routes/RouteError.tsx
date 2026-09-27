import { Button } from '@maxhub/max-ui'
import { TriangleAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useRouteError } from 'react-router'
import { EmptyState } from '@/shared/ui/empty-state'
import { StatusScreen } from '@/shared/ui/status-screen'
import {
  canReloadForNewBuild,
  isChunkLoadError,
  reloadForNewBuild,
} from '../entrypoint/stale-build'

const TITLE = 'Что-то пошло не так'
const TEXT = 'Страница не смогла открыться. Обновите её — обычно это помогает.'

// Replaces React Router's developer page ("Unexpected Application Error!") for any crash in a route.
// `inline` keeps the panel around it: only the section that broke shows the error.
export function RouteError({ inline = false }: { inline?: boolean }) {
  const error = useRouteError()
  // A chunk missing after a deploy: reload once to pick up the new build. If the page has just
  // done that and the file is still missing, show the usual error instead of reloading in a loop.
  const [reloading] = useState(() => isChunkLoadError(error) && canReloadForNewBuild())

  useEffect(() => {
    if (reloading) {
      reloadForNewBuild()
    }
  }, [reloading])

  if (import.meta.env.DEV) {
    console.error(error)
  }

  const actions = (
    <div className="flex flex-wrap justify-center gap-2">
      <Button onClick={() => window.location.reload()}>Обновить</Button>
      {/* A full page load, not router navigation: the app state may be what broke. */}
      <Button asChild variant="secondary">
        <a href="/">На главную</a>
      </Button>
    </div>
  )
  const title = reloading ? 'Загружаем новую версию…' : TITLE
  const text = reloading ? 'Панель обновилась, пока страница была открыта.' : TEXT

  if (inline) {
    return (
      <EmptyState
        icon={<TriangleAlert size={48} strokeWidth={1.5} />}
        title={title}
        text={text}
        action={actions}
      />
    )
  }
  return <StatusScreen title={title} text={text} action={actions} />
}
