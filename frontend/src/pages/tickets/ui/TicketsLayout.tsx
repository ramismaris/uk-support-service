import { Outlet, useMatch } from 'react-router'
import { routePaths } from '@/shared/config'
import { CloseUndoToast } from './CloseUndoToast'
import { TicketList } from './TicketList'

export function TicketsLayout() {
  const hasTicket = useMatch(routePaths.ticket) !== null
  return (
    <div className="flex min-h-0 flex-1">
      <section
        className={`${hasTicket ? 'hidden lg:flex' : 'flex'} w-full shrink-0 flex-col border-line lg:w-80 lg:border-r xl:w-96`}
      >
        <TicketList />
      </section>
      <div className={`${hasTicket ? 'flex' : 'hidden lg:flex'} min-w-0 flex-1`}>
        <Outlet />
      </div>
      <CloseUndoToast />
    </div>
  )
}
