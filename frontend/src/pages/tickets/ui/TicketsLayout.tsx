import { Outlet, useMatch } from 'react-router'
import { routePaths } from '@/shared/config'
import { TicketList } from './TicketList'

export function TicketsLayout() {
  const hasTicket = useMatch(routePaths.ticket) !== null
  return (
    <div className="flex min-h-0 flex-1">
      <section
        className={`${hasTicket ? 'hidden lg:flex' : 'flex'} w-full shrink-0 flex-col border-neutral-200 lg:w-80 lg:border-r xl:w-96 dark:border-neutral-800`}
      >
        <TicketList />
      </section>
      <div className={`${hasTicket ? 'flex' : 'hidden lg:flex'} min-w-0 flex-1`}>
        <Outlet />
      </div>
    </div>
  )
}
