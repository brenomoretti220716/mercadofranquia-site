import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createAdditionalFranchise } from '@/src/services/franchises'
import { createFranchisorRequest } from '@/src/services/users'
import { franchiseKeys } from '@/src/queries/franchises'
import type { CreateAdditionalFranchiseDto } from '@/src/schemas/franchises/CreateAdditionalFranchise'
import type { CreateFranchisorRequestDto } from '@/src/schemas/users/FranchisorRequest'
import { useAuth } from '../users/useAuth'

/**
 * Input unificado do form de cadastrar franquia.
 * O hook decide internamente qual endpoint backend chamar.
 */
export interface SubmitFranchiseRequestInput {
  mode: 'NEW' | 'EXISTING'
  streamName?: string // obrigatório se mode=NEW
  franchiseId?: string // obrigatório se mode=EXISTING
  claimReason?: string // obrigatório se mode=EXISTING
  // Campos opcionais só pra mode=NEW em user FRANCHISOR (marca adicional):
  description?: string
  detailedDescription?: string
  logoUrl?: string
  segment?: string
  subsegment?: string
  headquarter?: string
  headquarterState?: string
}

/**
 * Mutation unificada pra cadastrar franquia. Escolhe o endpoint certo:
 *
 * - User NÃO-FRANCHISOR (MEMBER, primeira marca):
 *   Chama POST /users/franchisor-request
 *   Backend cria Franchise + FranchisorRequest
 *   Admin aprova → user vira FRANCHISOR + Franchise vira APPROVED
 *
 * - User JÁ FRANCHISOR (marca adicional):
 *   Chama POST /franchisor/franchises (só se mode=NEW)
 *   OU POST /users/franchisor-request (se mode=EXISTING — reivindicação)
 *   Backend cria só Franchise (ou registra reivindicação)
 *
 * Invalida caches relevantes em sucesso.
 */
export function useSubmitFranchiseRequest() {
  const { token, payload } = useAuth()
  const queryClient = useQueryClient()
  const isFranchisor = payload?.role === 'FRANCHISOR'

  return useMutation({
    mutationFn: async (data: SubmitFranchiseRequestInput) => {
      // Reivindicação (EXISTING) sempre vai pelo fluxo de request, pra qualquer role
      if (data.mode === 'EXISTING') {
        const dto: CreateFranchisorRequestDto = {
          mode: 'EXISTING',
          franchiseId: data.franchiseId,
          claimReason: data.claimReason,
        }
        return await createFranchisorRequest(token!, dto)
      }

      // Mode NEW + user já FRANCHISOR → endpoint de marca adicional (mais campos)
      if (isFranchisor) {
        const dto: CreateAdditionalFranchiseDto = {
          streamName: data.streamName!,
          ...(data.description ? { description: data.description } : {}),
          ...(data.detailedDescription
            ? { detailedDescription: data.detailedDescription }
            : {}),
          ...(data.logoUrl ? { logoUrl: data.logoUrl } : {}),
          ...(data.segment ? { segment: data.segment } : {}),
          ...(data.subsegment ? { subsegment: data.subsegment } : {}),
          ...(data.headquarter ? { headquarter: data.headquarter } : {}),
          ...(data.headquarterState
            ? { headquarterState: data.headquarterState.toUpperCase() }
            : {}),
        }
        return await createAdditionalFranchise(dto, token!)
      }

      // Mode NEW + user NÃO é FRANCHISOR → primeira marca via fluxo de request
      const dto: CreateFranchisorRequestDto = {
        mode: 'NEW',
        streamName: data.streamName,
      }
      return await createFranchisorRequest(token!, dto)
    },
    onSuccess: () => {
      // Invalida tudo que pode ter mudado:
      // - myFranchises (nova marca PENDING pode aparecer)
      // - my-request (nova request pode ter sido criada)
      queryClient.invalidateQueries({
        queryKey: franchiseKeys.myFranchises(),
      })
      queryClient.invalidateQueries({
        queryKey: ['franchisor-request', 'my-request'],
      })
    },
  })
}
