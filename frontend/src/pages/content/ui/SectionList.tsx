import { Button } from '@maxhub/max-ui'
import { SearchX } from 'lucide-react'
import { Link, useParams } from 'react-router'
import { contentPath } from '@/shared/config'
import { EmptyState } from '@/shared/ui/empty-state'
import { NavMenuButton } from '@/widgets/app-shell'
import { isFilled, SECTIONS, sectionTitles } from '../lib/sections'
import { useContent } from '../model/use-content'

export function SectionList() {
  const content = useContent()
  // /staff/content without a section shows the welcome editor on wide screens.
  const current = useParams().section ?? 'welcome'

  return (
    <>
      <div className="flex flex-col gap-0.5 border-b border-line p-3">
        <div className="flex items-center gap-2">
          <NavMenuButton />
          <h1 className="text-lg font-semibold">Контент бота</h1>
        </div>
        <p className="text-sm text-fg-2">Что бот показывает жильцам в меню</p>
      </div>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        {content.isError ? (
          <EmptyState
            icon={<SearchX size={48} strokeWidth={1.5} />}
            title="Не удалось загрузить контент"
            text={content.error.message}
            action={<Button onClick={() => void content.refetch()}>Повторить</Button>}
          />
        ) : (
          SECTIONS.map((section) => (
            <Link
              key={section}
              to={contentPath(section)}
              aria-current={current === section ? 'page' : undefined}
              className={`flex items-center justify-between gap-2 border-b border-line px-3 py-3.5 transition-colors ${
                current === section ? 'bg-brand/10' : 'hover:bg-hover'
              }`}
            >
              <span className="font-medium">{sectionTitles[section]}</span>
              {content.isSuccess && !isFilled(content.data, section) && (
                <span className="text-xs text-fg-3">Не заполнен</span>
              )}
            </Link>
          ))
        )}
      </div>
    </>
  )
}
