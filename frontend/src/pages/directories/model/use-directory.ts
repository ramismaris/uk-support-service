import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createBuilding,
  createCategory,
  fetchBuildings,
  fetchCategories,
  reorderCategories,
  updateBuilding,
  updateCategory,
  type DirectoryItem,
} from '../api/directories'

export type DirectoryKind = 'buildings' | 'categories'

interface Change {
  id: number
  name?: string
  active?: boolean
}

const sources = {
  buildings: {
    key: ['admin', 'buildings'] as const,
    list: fetchBuildings,
    create: createBuilding,
    update: (change: Change) => updateBuilding(change.id, change),
  },
  categories: {
    key: ['admin', 'categories'] as const,
    list: fetchCategories,
    create: createCategory,
    update: (change: Change) => updateCategory(change.id, change),
  },
}

export function useDirectory(kind: DirectoryKind) {
  const queryClient = useQueryClient()
  const source = sources[kind]
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: source.key })
    // The broadcast form and the ticket filters read the same buildings and categories.
    void queryClient.invalidateQueries({ queryKey: ['staff', kind] })
  }

  const list = useQuery({ queryKey: source.key, queryFn: source.list })

  const create = useMutation({ mutationFn: source.create, onSuccess: refresh })

  const update = useMutation({
    mutationFn: source.update,
    onSuccess: (item) => {
      queryClient.setQueryData<DirectoryItem[]>(source.key, (items) =>
        items?.map((current) => (current.id === item.id ? item : current)),
      )
      refresh()
    },
  })

  // The new order shows at once; a failed save puts the old one back and rereads the list.
  const reorder = useMutation({
    mutationFn: reorderCategories,
    onMutate: (ids: number[]) => {
      const previous = queryClient.getQueryData<DirectoryItem[]>(source.key)
      queryClient.setQueryData<DirectoryItem[]>(source.key, (items) =>
        items ? ids.flatMap((id) => items.filter((item) => item.id === id)) : items,
      )
      return { previous }
    },
    onError: (_error, _ids, context) => {
      queryClient.setQueryData(source.key, context?.previous)
      refresh()
    },
    onSuccess: (items) => {
      queryClient.setQueryData(source.key, items)
      refresh()
    },
  })

  return { list, create, update, reorder }
}
