import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchContent, saveSection } from '../api/content'
import type { Drafts, Section } from '../lib/sections'

export const contentKey = ['admin', 'content'] as const

export function useContent() {
  return useQuery({ queryKey: contentKey, queryFn: fetchContent })
}

export function useSaveSection<S extends Section>(section: S) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (draft: Drafts[S]) => saveSection(section, draft),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: contentKey }),
  })
}
