import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createAdditionalFranchise } from '@/src/services/franchises'
import type { CreateAdditionalFranchiseDto } from '@/src/schemas/franchises/CreateAdditionalFranchise'
import { franchiseKeys } from '@/src/queries/franchises'
import { useAuth } from '../users/useAuth'

/**
 * Mutation para franqueador aprovado criar uma marca adicional.
 * Endpoint: POST /franchisor/franchises
 *
 * Em success, invalida o cache de myFranchises pra que a listagem
 * do painel reflita a nova franquia PENDING imediatamente.
 *
 * Toasts e erros são responsabilidade do componente consumer
 * (via onSuccess/onError do mutate()).
 */
export function useCreateAdditionalFranchise() {
  const { token } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateAdditionalFranchiseDto) =>
      createAdditionalFranchise(data, token!),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: franchiseKeys.myFranchises(),
      })
    },
  })
}
