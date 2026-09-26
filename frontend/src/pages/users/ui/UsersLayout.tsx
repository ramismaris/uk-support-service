import { Users } from 'lucide-react'
import { Outlet, useMatch } from 'react-router'
import { routePaths } from '@/shared/config'
import { EmptyState } from '@/shared/ui/empty-state'
import { UserList } from './UserList'

export function UsersIndex() {
  return (
    <EmptyState
      icon={<Users size={48} strokeWidth={1.5} />}
      title="Выберите пользователя"
      text="Здесь меняются роли и блокировка."
    />
  )
}

export function UsersLayout() {
  const hasUser = useMatch(routePaths.user) !== null
  return (
    <div className="flex min-h-0 flex-1">
      <section
        className={`${hasUser ? 'hidden lg:flex' : 'flex'} w-full shrink-0 flex-col border-line lg:w-80 lg:border-r xl:w-96`}
      >
        <UserList />
      </section>
      <div className={`${hasUser ? 'flex' : 'hidden lg:flex'} min-w-0 flex-1`}>
        <Outlet />
      </div>
    </div>
  )
}
