import { Outlet, useMatch } from 'react-router'
import { routePaths } from '@/shared/config'
import { SectionList } from './SectionList'

export function ContentLayout() {
  const hasSection = useMatch(routePaths.contentSection) !== null
  return (
    <div className="flex min-h-0 flex-1">
      <section
        className={`${hasSection ? 'hidden lg:flex' : 'flex'} w-full shrink-0 flex-col border-line lg:w-72 lg:border-r`}
      >
        <SectionList />
      </section>
      <div className={`${hasSection ? 'flex' : 'hidden lg:flex'} min-w-0 flex-1`}>
        <Outlet />
      </div>
    </div>
  )
}
