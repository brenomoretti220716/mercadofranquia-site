import { stripNonDigits } from '@/src/utils/formaters'
import { z } from 'zod'

export const FranchisorStepTwoSchema = z.object({
  name: z.string().min(1, 'Esse campo é obrigatório'),
  phone: z
    .string({ required_error: 'Esse campo é obrigatório' })
    .min(1, { message: 'Esse campo é obrigatório' })
    .refine(
      (val) => {
        const digits = stripNonDigits(val)
        return digits.length === 10 || digits.length === 11
      },
      { message: 'Telefone deve ter 10 ou 11 dígitos' },
    ),
  jobTitle: z
    .string({ required_error: 'Esse campo é obrigatório' })
    .trim()
    .min(1, 'Esse campo é obrigatório')
    .max(100, 'Cargo deve ter no máximo 100 caracteres'),
})

export type FranchisorStepTwoInput = z.infer<typeof FranchisorStepTwoSchema>
