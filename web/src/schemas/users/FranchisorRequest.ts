import { z } from 'zod'

/**
 * FranchisorRequest schema — aligned with FastAPI backend (post Sprint 1, 20/04/2026).
 *
 * Legacy fields removed: cnpj, responsable, responsableRole, commercialEmail,
 * commercialPhone, cnpjCardPath, socialContractPath.
 *
 * New fields: mode, franchiseId, claimReason, hubspotCompanyId.
 */

export enum FranchisorRequestStatus {
  PENDING = 'PENDING',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED',
  UNDER_REVIEW = 'UNDER_REVIEW',
  CANCELLED = 'CANCELLED',
}

export type FranchisorRequestMode = 'NEW' | 'EXISTING'

export interface FranchisorRequestFranchiseSummary {
  id: string
  name: string
  slug: string | null
  logoUrl: string | null
  status: 'PENDING' | 'APPROVED' | 'REJECTED'
  isActive: boolean
}

export interface FranchisorRequest {
  id: string
  userId: string
  streamName: string
  mode: FranchisorRequestMode
  franchiseId: string | null
  claimReason: string | null
  hubspotCompanyId: string | null
  status: FranchisorRequestStatus
  rejectionReason: string | null
  reviewedBy: string | null
  reviewedAt: string | null
  createdAt: string
  updatedAt: string
  user?: {
    id: string
    name: string
    email: string
  }
  franchise?: FranchisorRequestFranchiseSummary | null
}

/**
 * Body pra POST /users/franchisor-request
 */
export interface CreateFranchisorRequestDto {
  mode: FranchisorRequestMode
  streamName?: string // obrigatório se mode=NEW
  franchiseId?: string // obrigatório se mode=EXISTING
  claimReason?: string // obrigatório se mode=EXISTING
}

export interface RejectFranchisorRequestDto {
  rejectionReason: string
}

/**
 * Zod schema pro form unificado NEW/EXISTING.
 * Validação condicional: streamName obrigatório em NEW; franchiseId + claimReason em EXISTING.
 */
export const FranchisorRequestFormSchema = z
  .object({
    mode: z.enum(['NEW', 'EXISTING']),
    streamName: z.string().trim().optional(),
    franchiseId: z.string().trim().optional(),
    claimReason: z.string().trim().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.mode === 'NEW') {
      if (!data.streamName || data.streamName.length < 2) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['streamName'],
          message: 'Nome da marca é obrigatório (mínimo 2 caracteres)',
        })
      }
    } else if (data.mode === 'EXISTING') {
      if (!data.franchiseId) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['franchiseId'],
          message: 'Selecione a franquia que você quer reivindicar',
        })
      }
      if (!data.claimReason || data.claimReason.length < 10) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['claimReason'],
          message: 'Explique por que você é o dono (mínimo 10 caracteres)',
        })
      }
    }
  })

export type FranchisorRequestFormInput = z.infer<
  typeof FranchisorRequestFormSchema
>
