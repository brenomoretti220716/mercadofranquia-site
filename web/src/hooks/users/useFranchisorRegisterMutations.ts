import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import Api from '@/src/api/Api'
import { Payload } from '@/src/schemas/auth/auth'
import { StepOneRegistrationInput } from '@/src/schemas/users/auth'
import { formatErrorMessage, handleHttpError } from '@/src/utils/errorHandlers'
import { stripNonDigits } from '@/src/utils/formaters'
import { setClientAuthCookie } from '@/src/utils/clientCookie'
import { FranchisorStepTwoInput } from '@/src/schemas/users/franchisorAuth'

export type FranchisorStepOnePayload = StepOneRegistrationInput &
  FranchisorStepTwoInput

interface StepOneResponse {
  user?: Payload
  access_token?: string
}

export function useFranchisorStepOneMutation(options?: {
  onSuccess?: (data: StepOneResponse) => void
}) {
  return useMutation({
    mutationFn: async (data: FranchisorStepOnePayload) => {
      const body = {
        name: data.name,
        email: data.email,
        password: data.password,
        phone: stripNonDigits(data.phone),
        profileType: 'FRANCHISOR' as const,
        jobTitle: data.jobTitle,
      }

      const response = await fetch(Api('/users/register/step-one'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (response.status === 409) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(
          errorData?.message || 'Já existe uma conta com esses dados.',
        )
      }

      if (!response.ok) {
        throw new Error(
          handleHttpError(
            response,
            'Não foi possível concluir o cadastro. Tente novamente.',
          ),
        )
      }

      return (await response.json()) as StepOneResponse
    },
    onSuccess: (data) => {
      const accessToken = data?.access_token
      if (accessToken && typeof accessToken === 'string') {
        setClientAuthCookie(accessToken)
        options?.onSuccess?.(data)
      } else {
        toast.error('Erro ao processar cadastro. Token não recebido.')
      }
    },
    onError: (error) => {
      toast.error(
        formatErrorMessage(
          error,
          'Não foi possível concluir o cadastro. Tente novamente.',
        ),
      )
    },
  })
}
