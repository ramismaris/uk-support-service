import {
  useInfiniteQuery,
  useMutation,
  useQueryClient,
  type InfiniteData,
} from '@tanstack/react-query'
import { fetchUsers, updateUser, type AdminUser, type UserUpdate } from '../api/users'
import { userFilterToQuery, type UserSearch } from '../lib/filters'

type UsersPage = { total: number; items: AdminUser[] }

export const usersKey = ['admin', 'users'] as const

export function useUsers(search: UserSearch) {
  const query = userFilterToQuery(search.filter, search.q)
  return useInfiniteQuery({
    queryKey: [...usersKey, query],
    queryFn: ({ pageParam }) => fetchUsers(query, pageParam),
    initialPageParam: 0,
    getNextPageParam: (_last, pages) => {
      const loaded = pages.reduce((count, page) => count + page.items.length, 0)
      return loaded < (pages.at(-1)?.total ?? 0) ? loaded : undefined
    },
  })
}

export function useUpdateUser(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (update: UserUpdate) => updateUser(id, update),
    onSuccess: (user) => {
      // Update the row in place so the card keeps showing it; filtered lists refetch later.
      queryClient.setQueriesData<InfiniteData<UsersPage>>({ queryKey: usersKey }, (data) =>
        data
          ? {
              ...data,
              pages: data.pages.map((page) => ({
                ...page,
                items: page.items.map((item) => (item.id === user.id ? user : item)),
              })),
            }
          : data,
      )
      void queryClient.invalidateQueries({ queryKey: usersKey, refetchType: 'none' })
    },
  })
}
