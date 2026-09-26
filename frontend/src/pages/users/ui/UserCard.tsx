import { Button } from '@maxhub/max-ui'
import { ChevronLeft, UserRound } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link, useLocation, useParams, useSearchParams } from 'react-router'
import { useMe } from '@/entities/session'
import { roleLabels, type UserRole } from '@/entities/user'
import { routePaths } from '@/shared/config'
import { formatDateTime } from '@/shared/lib/format'
import { ConfirmDialog } from '@/shared/ui/confirm-dialog'
import { EmptyState } from '@/shared/ui/empty-state'
import type { AdminUser } from '../api/users'
import { parseUserSearch } from '../lib/filters'
import { canEditUser, confirmText, type UserAction } from '../lib/permissions'
import { useUpdateUser, useUsers } from '../model/users'
import { userName } from '../lib/names'
import { UserInitials } from './UserRow'

const ROLES: UserRole[] = ['CLIENT', 'MANAGER', 'ADMIN']

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex gap-3 text-sm">
      <span className="w-36 shrink-0 text-fg-3">{label}</span>
      <span className="min-w-0 flex-1">{children}</span>
    </div>
  )
}

function UserDetails({ user }: { user: AdminUser }) {
  const { data: me } = useMe()
  const update = useUpdateUser(user.id)
  const [pending, setPending] = useState<UserAction | null>(null)
  const permission = me ? canEditUser(me, user) : { editable: false, reason: null }
  const copy = pending ? confirmText(pending) : null

  const apply = (action: UserAction) => {
    const body =
      action.kind === 'role' ? { role: action.to } : { is_blocked: action.kind === 'block' }
    update.mutate(body, { onSuccess: () => setPending(null) })
  }

  // Role changes that need no confirmation apply at once; the rest go through the dialog.
  const request = (action: UserAction) => {
    if (confirmText(action)) {
      update.reset()
      setPending(action)
    } else {
      apply(action)
    }
  }

  return (
    <div className="flex max-w-xl flex-col gap-6 p-4 lg:p-6">
      <div className="flex items-center gap-3">
        <UserInitials user={user} size="size-14" />
        <div className="min-w-0">
          <div className="truncate text-lg font-semibold">{userName(user)}</div>
          <div className="text-sm text-fg-3">
            {user.username ? `@${user.username} · ` : ''}
            {roleLabels[user.role]}
            {user.is_blocked && <span className="text-negative"> · Заблокирован</span>}
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        {user.phone && (
          <Row label="Телефон">
            <a className="text-brand" href={`tel:+${user.phone.replace(/^\+/, '')}`}>
              {user.phone}
            </a>
          </Row>
        )}
        <Row label="Max id">{user.max_user_id}</Row>
        <Row label="Регистрация">{formatDateTime(user.created_at)}</Row>
        <Row label="Последний визит">
          {user.last_seen_at ? formatDateTime(user.last_seen_at) : 'Не заходил'}
        </Row>
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-sm font-medium">Роль</span>
        <div
          role="radiogroup"
          aria-label="Роль"
          className="inline-flex self-start rounded-xl bg-fill p-1"
        >
          {ROLES.map((role) => (
            <button
              key={role}
              type="button"
              role="radio"
              aria-checked={user.role === role}
              disabled={!permission.editable || update.isPending}
              onClick={() =>
                role !== user.role && request({ kind: 'role', from: user.role, to: role })
              }
              className={`rounded-lg px-3 py-1.5 text-sm transition-colors disabled:cursor-not-allowed ${
                user.role === role
                  ? 'bg-layer font-medium text-fg'
                  : 'text-fg-2 enabled:hover:text-fg'
              }`}
            >
              {roleLabels[role]}
            </button>
          ))}
        </div>
        {permission.reason && <span className="text-xs text-fg-3">{permission.reason}</span>}
      </div>

      <div className="flex flex-col items-start gap-2">
        <Button
          variant={user.is_blocked ? 'secondary' : 'destructive'}
          size="small"
          disabled={!permission.editable || update.isPending}
          onClick={() => request({ kind: user.is_blocked ? 'unblock' : 'block' })}
        >
          {user.is_blocked ? 'Разблокировать' : 'Заблокировать'}
        </Button>
        {update.error && !pending && (
          <p role="alert" className="text-sm text-negative">
            {update.error.message}
          </p>
        )}
      </div>

      <ConfirmDialog
        open={copy !== null}
        title={copy?.title ?? ''}
        text={copy?.text ?? ''}
        confirmLabel={copy?.confirmLabel ?? ''}
        destructive={copy?.destructive}
        pending={update.isPending}
        error={update.error?.message}
        onConfirm={() => pending && apply(pending)}
        onCancel={() => setPending(null)}
      />
    </div>
  )
}

export function UserCard() {
  const id = Number(useParams().id)
  const [params] = useSearchParams()
  const { search } = useLocation()
  // There is no "get one user" endpoint: the card shows the user from the loaded list.
  const users = useUsers(parseUserSearch(params))
  const user = users.data?.pages.flatMap((page) => page.items).find((item) => item.id === id)

  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-y-auto">
      <header className="flex items-center gap-2 border-b border-line px-3 py-3 lg:hidden">
        <Link
          to={{ pathname: routePaths.users, search }}
          aria-label="К списку"
          className="-ml-1 rounded-full p-1 hover:bg-hover"
        >
          <ChevronLeft size={20} strokeWidth={2} />
        </Link>
        <span className="font-semibold">Пользователь</span>
      </header>
      {user ? (
        // Keyed: a pending change or its error must not carry over to the next user.
        <UserDetails key={user.id} user={user} />
      ) : users.isPending ? (
        <div className="m-auto text-sm text-fg-3">Загрузка…</div>
      ) : (
        <EmptyState
          icon={<UserRound size={48} strokeWidth={1.5} />}
          title="Откройте пользователя из списка"
          action={
            <Button asChild variant="secondary">
              <Link to={routePaths.users}>К списку</Link>
            </Button>
          }
        />
      )}
    </section>
  )
}
