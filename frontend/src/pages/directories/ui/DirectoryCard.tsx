import { Button } from '@maxhub/max-ui'
import type { LucideIcon } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Card } from '@/shared/ui/card'
import { moveId } from '../lib/order'
import { ACTIVE_LIMIT, activeCount, atLimit } from '../lib/limits'
import { normalizeName, validateName } from '../lib/name'
import { useDirectory, type DirectoryKind } from '../model/use-directory'
import { DirectoryRow } from './DirectoryRow'

interface DirectoryCardProps {
  kind: DirectoryKind
  title: string
  icon: LucideIcon
  placeholder: string
  // A line under the form: what the name is used for.
  hint: string
}

export function DirectoryCard({ kind, title, icon, placeholder, hint }: DirectoryCardProps) {
  const { list, create, update, reorder } = useDirectory(kind)
  const [name, setName] = useState('')
  const [nameError, setNameError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)

  const items = list.data ?? []
  const full = atLimit(items)
  const ids = items.map((item) => item.id)

  const add = (event: FormEvent) => {
    event.preventDefault()
    const problem = validateName(name)
    setNameError(problem)
    if (problem) {
      return
    }
    create.mutate(normalizeName(name), {
      onSuccess: () => {
        setName('')
        setSaveError(null)
      },
      onError: (error) => setNameError(error.message),
    })
  }

  const rename = async (id: number, next: string): Promise<boolean> => {
    try {
      await update.mutateAsync({ id, name: next })
      setSaveError(null)
      return true
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'Не удалось сохранить')
      return false
    }
  }

  const toggle = (id: number, active: boolean) =>
    update.mutate(
      { id, active },
      {
        onSuccess: () => setSaveError(null),
        onError: (error) => setSaveError(error.message),
      },
    )

  const move = (id: number, delta: -1 | 1) =>
    reorder.mutate(moveId(ids, id, delta), {
      onSuccess: () => setSaveError(null),
      onError: (error) => setSaveError(error.message),
    })

  const body = () => {
    if (list.isPending) {
      return <div className="h-32 animate-pulse rounded-xl bg-fill" />
    }
    if (list.isError) {
      return (
        <div className="flex flex-col items-start gap-2">
          <p className="text-sm text-negative">{list.error.message}</p>
          <Button variant="secondary" size="small" onClick={() => void list.refetch()}>
            Повторить
          </Button>
        </div>
      )
    }
    return (
      <ul className="divide-y divide-line">
        {items.map((item, index) => (
          <DirectoryRow
            key={item.id}
            item={item}
            canEnable={!full}
            onMove={kind === 'categories' ? (delta) => move(item.id, delta) : undefined}
            canMoveUp={index > 0}
            canMoveDown={index < items.length - 1}
            onRename={(next) => rename(item.id, next)}
            onToggle={(active) => toggle(item.id, active)}
          />
        ))}
      </ul>
    )
  }

  return (
    <Card
      title={title}
      icon={icon}
      aside={
        <span>
          Включено {activeCount(items)} из {ACTIVE_LIMIT}
        </span>
      }
      bodyClassName="gap-4"
    >
      <form className="flex flex-col gap-1.5" onSubmit={add}>
        <div className="flex gap-2">
          <input
            value={name}
            placeholder={placeholder}
            aria-label={placeholder}
            aria-invalid={nameError ? true : undefined}
            onChange={(event) => {
              setName(event.target.value)
              setNameError(null)
            }}
            className="min-w-0 flex-1 rounded-xl bg-fill px-3 py-2 text-[15px] outline-none placeholder:text-fg-3 focus:ring-2 focus:ring-brand/40"
          />
          <Button type="submit" disabled={full} loading={create.isPending}>
            Добавить
          </Button>
        </div>
        {nameError ? (
          <span className="text-sm text-negative">{nameError}</span>
        ) : (
          <span className="text-xs text-fg-3">
            {full ? 'Включено 29 из 29: отключите что-нибудь, чтобы добавить новое.' : hint}
          </span>
        )}
      </form>
      {body()}
      {saveError && (
        <p role="alert" className="text-sm text-negative">
          {saveError}
        </p>
      )}
    </Card>
  )
}
