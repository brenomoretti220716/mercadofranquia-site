import { updateFranchisorFranchise } from '@/src/services/franchises'
import { formatErrorMessage } from '@/src/utils/errorHandlers'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

interface UpdateFranchisorFranchiseInput {
  franchiseId: string
  payload: Record<string, unknown>
  token: string
}

export function useUpdateFranchisorFranchise() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      franchiseId,
      payload,
      token,
    }: UpdateFranchisorFranchiseInput) =>
      updateFranchisorFranchise(franchiseId, payload, token),
    onSuccess: (_data, variables) => {
      toast.success('Alterações salvas.')
      queryClient.invalidateQueries({ queryKey: ['my-franchises'] })
      queryClient.invalidateQueries({
        queryKey: ['franchise', variables.franchiseId],
      })
      queryClient.invalidateQueries({ queryKey: ['franchises'] })
    },
    onError: (error: Error) => {
      toast.error(
        formatErrorMessage(error, 'Erro ao salvar alterações. Tente novamente.'),
      )
    },
  })
}
