import { fetchFontesStatus, type FontesStatus } from '@/src/services/fontes'
import { useQuery } from '@tanstack/react-query'

export const FONTES_STATUS_KEY = ['fontes-status'] as const

export function useFontesStatus() {
  return useQuery<FontesStatus>({
    queryKey: FONTES_STATUS_KEY,
    queryFn: fetchFontesStatus,
  })
}
