import { Button, CellAction, CellInput, CellList } from '@maxhub/max-ui'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { routePaths } from '@/shared/config'
import { seedUsers } from '../config/seed-users'
import { parseMaxUserId } from '../lib/parse-max-user-id'
import { useDevLogin } from '../model/use-dev-login'

export function DevLoginForm() {
  const navigate = useNavigate()
  const login = useDevLogin()
  const [customId, setCustomId] = useState('')
  const parsedId = parseMaxUserId(customId)

  const submit = (maxUserId: number) => {
    login.mutate(maxUserId, { onSuccess: () => navigate(routePaths.home, { replace: true }) })
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (parsedId !== null) {
      submit(parsedId)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <CellList mode="island" header="Демо-пользователи">
        {seedUsers.map((user) => (
          <CellAction
            key={user.maxUserId}
            showChevron
            disabled={login.isPending}
            onClick={() => submit(user.maxUserId)}
          >
            {user.label}
          </CellAction>
        ))}
      </CellList>

      <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
        <CellList mode="island" header="Другой пользователь">
          <CellInput
            placeholder="max_user_id"
            inputMode="numeric"
            value={customId}
            onChange={(event) => setCustomId(event.target.value)}
          />
        </CellList>
        <Button
          type="submit"
          size="large"
          stretched
          disabled={parsedId === null}
          loading={login.isPending}
        >
          Войти
        </Button>
      </form>

      {login.error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {login.error.message}
        </p>
      )}
    </div>
  )
}
