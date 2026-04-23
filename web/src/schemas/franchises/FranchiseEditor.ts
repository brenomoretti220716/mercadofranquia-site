import { z } from 'zod'

const CURRENT_YEAR = new Date().getFullYear()

const optionalString = z.string().optional().or(z.literal(''))

const optionalNumericString = z
  .string()
  .optional()
  .refine(
    (val) => {
      if (!val || val === '') return true
      return /^\d+(\.\d+)?$/.test(val)
    },
    { message: 'Use apenas números (ponto para decimais)' },
  )

const optionalIntegerString = z
  .string()
  .optional()
  .refine(
    (val) => {
      if (!val || val === '') return true
      return /^\d+$/.test(val)
    },
    { message: 'Use apenas números inteiros' },
  )

const optionalYearString = z
  .string()
  .optional()
  .refine(
    (val) => {
      if (!val || val === '') return true
      if (!/^\d{4}$/.test(val)) return false
      const n = parseInt(val, 10)
      return n >= 1800 && n <= CURRENT_YEAR + 1
    },
    { message: `Ano entre 1800 e ${CURRENT_YEAR + 1}` },
  )

export const FranchiseEditorInfoFormSchema = z
  .object({
    // Identidade
    name: z
      .string()
      .min(2, 'Nome precisa ter pelo menos 2 caracteres')
      .max(150, 'Nome muito longo')
      .optional()
      .or(z.literal('')),
    description: z.string().max(1000, 'Máximo 1000 caracteres').optional().or(z.literal('')),
    detailedDescription: z
      .string()
      .max(10000, 'Máximo 10000 caracteres')
      .optional()
      .or(z.literal('')),

    // Classificação
    segment: optionalString,
    subsegment: optionalString,
    businessType: optionalString,

    // Localização e unidades
    headquarter: optionalString,
    headquarterState: z
      .string()
      .max(2, 'Use a sigla do estado (2 letras)')
      .optional()
      .or(z.literal('')),
    totalUnits: optionalIntegerString,
    totalUnitsInBrazil: optionalIntegerString,
    unitsEvolution: z.enum(['UP', 'DOWN', 'MAINTAIN']).optional().or(z.literal('')),

    // Histórico
    brandFoundationYear: optionalYearString,
    franchiseStartYear: optionalYearString,
    abfSince: optionalYearString,
    isAbfAssociated: z.boolean().optional(),

    // Contato (1-1 com ContactInfo no backend)
    contactPhone: z
      .string()
      .optional()
      .or(z.literal(''))
      .refine(
        (val) => {
          if (!val || val === '') return true
          const digits = val.replace(/\D/g, '')
          return digits.length >= 10 && digits.length <= 11
        },
        { message: 'Telefone deve ter 10 ou 11 dígitos' },
      ),
    contactEmail: z
      .string()
      .optional()
      .or(z.literal(''))
      .refine(
        (val) => {
          if (!val || val === '') return true
          return z.string().email().safeParse(val).success
        },
        { message: 'E-mail inválido' },
      ),
    contactWebsite: z
      .string()
      .optional()
      .or(z.literal(''))
      .refine(
        (val) => {
          if (!val || val === '') return true
          try {
            const u = new URL(val)
            return u.protocol === 'http:' || u.protocol === 'https:'
          } catch {
            return false
          }
        },
        { message: 'URL precisa começar com http:// ou https://' },
      ),
  })
  .refine(
    (data) => {
      if (!data.abfSince) return true
      return data.isAbfAssociated !== false
    },
    {
      message: 'Preencher "Associada à ABF" para informar o ano',
      path: ['abfSince'],
    },
  )

export type FranchiseEditorInfoFormInput = z.infer<
  typeof FranchiseEditorInfoFormSchema
>

// ============================================================
// Investment tab schema — Sprint 4 Fatia 2
// 13 campos numéricos (Decimal no backend).
// ============================================================

const CALCULATION_BASE_OPTIONS = ['FATURAMENTO_BRUTO', 'FATURAMENTO_LIQUIDO'] as const

export const FranchiseEditorInvestmentFormSchema = z
  .object({
    minimumInvestment: optionalNumericString,
    maximumInvestment: optionalNumericString,

    franchiseFee: optionalNumericString,
    setupCapital: optionalNumericString,
    workingCapital: optionalNumericString,

    royalties: optionalNumericString,
    advertisingFee: optionalNumericString,
    calculationBaseRoyaltie: z
      .enum(CALCULATION_BASE_OPTIONS)
      .optional()
      .or(z.literal('')),
    calculationBaseAdFee: z
      .enum(CALCULATION_BASE_OPTIONS)
      .optional()
      .or(z.literal('')),

    minimumReturnOnInvestment: optionalIntegerString,
    maximumReturnOnInvestment: optionalIntegerString,
    averageMonthlyRevenue: optionalNumericString,

    storeArea: optionalIntegerString,
  })
  .refine(
    (data) => {
      if (!data.minimumInvestment || !data.maximumInvestment) return true
      return (
        parseFloat(data.maximumInvestment) >= parseFloat(data.minimumInvestment)
      )
    },
    {
      message: 'Investimento máximo deve ser maior ou igual ao mínimo',
      path: ['maximumInvestment'],
    },
  )
  .refine(
    (data) => {
      if (!data.minimumReturnOnInvestment || !data.maximumReturnOnInvestment)
        return true
      return (
        parseInt(data.maximumReturnOnInvestment) >=
        parseInt(data.minimumReturnOnInvestment)
      )
    },
    {
      message: 'ROI máximo deve ser maior ou igual ao mínimo',
      path: ['maximumReturnOnInvestment'],
    },
  )

export type FranchiseEditorInvestmentFormInput = z.infer<
  typeof FranchiseEditorInvestmentFormSchema
>

/**
 * Converte form (strings) → payload PATCH, só campos dirty.
 * Inteiros entram como number inteiro; decimais entram como number float.
 * Strings de enum (calculationBase*) vazias viram null (limpar).
 */
export function normalizeFranchiseEditorInvestmentPayload(
  data: FranchiseEditorInvestmentFormInput,
  dirtyFields: Partial<
    Record<keyof FranchiseEditorInvestmentFormInput, boolean>
  >,
): Record<string, unknown> {
  const out: Record<string, unknown> = {}

  const setFloat = (key: keyof FranchiseEditorInvestmentFormInput) => {
    if (!dirtyFields[key]) return
    const raw = data[key]
    if (raw === undefined || raw === '' || raw === null) {
      out[key] = null
      return
    }
    if (typeof raw !== 'string') return
    const n = parseFloat(raw)
    out[key] = Number.isNaN(n) ? null : n
  }

  const setInt = (key: keyof FranchiseEditorInvestmentFormInput) => {
    if (!dirtyFields[key]) return
    const raw = data[key]
    if (raw === undefined || raw === '' || raw === null) {
      out[key] = null
      return
    }
    if (typeof raw !== 'string') return
    const n = parseInt(raw.replace(/\./g, ''), 10)
    out[key] = Number.isNaN(n) ? null : n
  }

  const setEnum = (key: keyof FranchiseEditorInvestmentFormInput) => {
    if (!dirtyFields[key]) return
    const v = data[key]
    if (v === 'FATURAMENTO_BRUTO' || v === 'FATURAMENTO_LIQUIDO') {
      out[key] = v
    } else {
      out[key] = null
    }
  }

  setFloat('minimumInvestment')
  setFloat('maximumInvestment')
  setFloat('franchiseFee')
  setFloat('setupCapital')
  setFloat('workingCapital')
  setFloat('royalties')
  setFloat('advertisingFee')
  setFloat('averageMonthlyRevenue')

  setInt('minimumReturnOnInvestment')
  setInt('maximumReturnOnInvestment')
  setInt('storeArea')

  setEnum('calculationBaseRoyaltie')
  setEnum('calculationBaseAdFee')

  return out
}

/**
 * Mapeia o form input (strings) → payload aceito pelo PATCH
 * /franchisor/franchises/{id}. Só inclui campos efetivamente alterados
 * (dirty fields), pra preservar semântica PATCH do backend
 * (`exclude_unset=True` no Pydantic).
 */
export function normalizeFranchiseEditorPayload(
  data: FranchiseEditorInfoFormInput,
  dirtyFields: Partial<Record<keyof FranchiseEditorInfoFormInput, boolean>>,
): Record<string, unknown> {
  const out: Record<string, unknown> = {}

  const setString = (key: keyof FranchiseEditorInfoFormInput) => {
    if (!dirtyFields[key]) return
    const raw = data[key]
    if (raw === undefined) return
    if (typeof raw !== 'string') return
    const trimmed = raw.trim()
    out[key] = trimmed === '' ? null : trimmed
  }

  const setInt = (key: keyof FranchiseEditorInfoFormInput) => {
    if (!dirtyFields[key]) return
    const raw = data[key]
    if (raw === undefined || raw === '' || raw === null) {
      out[key] = null
      return
    }
    if (typeof raw !== 'string') return
    const n = parseInt(raw.replace(/\./g, ''), 10)
    out[key] = Number.isNaN(n) ? null : n
  }

  setString('name')
  setString('description')
  setString('detailedDescription')
  setString('segment')
  setString('subsegment')
  setString('businessType')
  setString('headquarter')
  setString('headquarterState')
  setInt('totalUnits')
  setInt('totalUnitsInBrazil')
  setInt('brandFoundationYear')
  setInt('franchiseStartYear')
  setInt('abfSince')

  if (dirtyFields.unitsEvolution) {
    const v = data.unitsEvolution
    out.unitsEvolution =
      v === 'UP' || v === 'DOWN' || v === 'MAINTAIN' ? v : null
  }

  if (dirtyFields.isAbfAssociated) {
    out.isAbfAssociated =
      typeof data.isAbfAssociated === 'boolean' ? data.isAbfAssociated : null
  }

  if (dirtyFields.contactPhone) {
    const raw = (data.contactPhone ?? '').replace(/\D/g, '')
    out.contactPhone = raw === '' ? '' : raw
  }
  if (dirtyFields.contactEmail) {
    out.contactEmail = (data.contactEmail ?? '').trim()
  }
  if (dirtyFields.contactWebsite) {
    const trimmed = (data.contactWebsite ?? '').trim()
    out.contactWebsite = trimmed === '' ? null : trimmed
  }

  return out
}
