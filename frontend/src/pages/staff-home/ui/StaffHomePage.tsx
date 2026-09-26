import { Typography } from '@maxhub/max-ui'
import { PageTransition } from '@/shared/ui/page-transition'

export function StaffHomePage() {
  return (
    <PageTransition className="p-4 lg:p-8">
      <Typography.Title>Обращения</Typography.Title>
      <p className="mt-2 text-neutral-500 dark:text-neutral-400">
        Здесь появится список обращений жильцов.
      </p>
    </PageTransition>
  )
}
