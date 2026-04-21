import { z } from 'zod'

/**
 * Schema pro form de criar franquia adicional por um franqueador já aprovado.
 * Endpoint: POST /franchisor/franchises
 */
export const CreateAdditionalFranchiseSchema = z.object({
  streamName: z
    .string()
    .trim()
    .min(2, 'Nome da marca deve ter pelo menos 2 caracteres')
    .max(150, 'Nome muito longo (máx. 150 caracteres)'),
  description: z.string().trim().max(1000).optional().or(z.literal('')),
  detailedDescription: z
    .string()
    .trim()
    .max(10000)
    .optional()
    .or(z.literal('')),
  logoUrl: z.string().trim().url('URL inválida').optional().or(z.literal('')),
  segment: z.string().trim().max(100).optional().or(z.literal('')),
  subsegment: z.string().trim().max(100).optional().or(z.literal('')),
  headquarter: z.string().trim().max(100).optional().or(z.literal('')),
  headquarterState: z
    .string()
    .trim()
    .length(2, 'UF deve ter 2 caracteres')
    .optional()
    .or(z.literal('')),
})

export type CreateAdditionalFranchiseInput = z.infer<
  typeof CreateAdditionalFranchiseSchema
>

/**
 * DTO enviado no body do POST. Strings vazias devem virar undefined antes de enviar.
 */
export interface CreateAdditionalFranchiseDto {
  streamName: string
  description?: string
  detailedDescription?: string
  logoUrl?: string
  segment?: string
  subsegment?: string
  headquarter?: string
  headquarterState?: string
}
