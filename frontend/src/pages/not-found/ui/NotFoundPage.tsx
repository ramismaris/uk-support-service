import { Button } from '@maxhub/max-ui'
import { Link } from 'react-router'
import { routePaths } from '@/shared/config'
import { StatusScreen } from '@/shared/ui/status-screen'

export function NotFoundPage() {
  return (
    <StatusScreen
      title="Страница не найдена"
      text="Возможно, ссылка устарела."
      action={
        <Button asChild variant="secondary">
          <Link to={routePaths.home}>На главную</Link>
        </Button>
      }
    />
  )
}
