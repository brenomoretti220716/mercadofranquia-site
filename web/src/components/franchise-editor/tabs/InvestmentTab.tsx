'use client'

import { useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import FormInput from '@/src/components/ui/FormInput'
import FormSelect from '@/src/components/ui/FormSelect'
import RoundedButton from '@/src/components/ui/RoundedButton'
import type { Franchise } from '@/src/schemas/franchises/Franchise'
import {
  FranchiseEditorInvestmentFormSchema,
  normalizeFranchiseEditorInvestmentPayload,
  type FranchiseEditorInvestmentFormInput,
} from '@/src/schemas/franchises/FranchiseEditor'
import { useUpdateFranchisorFranchise } from '@/src/hooks/franchises/useFranchisorFranchiseMutations'

const CALCULATION_BASE_OPTIONS = [
  { value: '', label: 'Selecione...' },
  { value: 'FATURAMENTO_BRUTO', label: 'Faturamento bruto' },
  { value: 'FATURAMENTO_LIQUIDO', label: 'Faturamento líquido' },
]

function toFormString(v: number | null | undefined): string {
  return typeof v === 'number' ? String(v) : ''
}

function franchiseToInvestmentDefaults(
  f: Franchise,
): FranchiseEditorInvestmentFormInput {
  const cbr = f.calculationBaseRoyaltie
  const cba = f.calculationBaseAdFee
  return {
    minimumInvestment: toFormString(f.minimumInvestment),
    maximumInvestment: toFormString(f.maximumInvestment),
    franchiseFee: toFormString(f.franchiseFee),
    setupCapital: toFormString(f.setupCapital),
    workingCapital: toFormString(f.workingCapital),
    royalties: toFormString(f.royalties),
    advertisingFee: toFormString(f.advertisingFee),
    calculationBaseRoyaltie:
      cbr === 'FATURAMENTO_BRUTO' || cbr === 'FATURAMENTO_LIQUIDO' ? cbr : '',
    calculationBaseAdFee:
      cba === 'FATURAMENTO_BRUTO' || cba === 'FATURAMENTO_LIQUIDO' ? cba : '',
    minimumReturnOnInvestment: toFormString(f.minimumReturnOnInvestment),
    maximumReturnOnInvestment: toFormString(f.maximumReturnOnInvestment),
    averageMonthlyRevenue: toFormString(f.averageMonthlyRevenue),
    storeArea: toFormString(f.storeArea),
  }
}

interface InvestmentTabProps {
  franchise: Franchise
  token: string
}

export default function InvestmentTab({
  franchise,
  token,
}: InvestmentTabProps) {
  const mutation = useUpdateFranchisorFranchise()

  const defaults = useMemo(
    () => franchiseToInvestmentDefaults(franchise),
    [franchise],
  )

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, dirtyFields, isDirty },
  } = useForm<FranchiseEditorInvestmentFormInput>({
    resolver: zodResolver(FranchiseEditorInvestmentFormSchema),
    defaultValues: defaults,
  })

  const isSubmitting = mutation.isPending

  const onSubmit = (data: FranchiseEditorInvestmentFormInput) => {
    const payload = normalizeFranchiseEditorInvestmentPayload(
      data,
      dirtyFields as Partial<
        Record<keyof FranchiseEditorInvestmentFormInput, boolean>
      >,
    )
    if (Object.keys(payload).length === 0) {
      toast.info('Nenhuma alteração pra salvar.')
      return
    }
    mutation.mutate(
      { franchiseId: franchise.id, payload, token },
      {
        onSuccess: (fresh) => {
          reset(franchiseToInvestmentDefaults(fresh))
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-foreground">
          Investimento total
        </h2>
        <p className="text-xs text-muted-foreground -mt-2">
          Faixa completa pra abrir uma unidade. Use ponto como separador decimal
          (ex: 450000.00).
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormInput
            label="Investimento mínimo (R$)"
            register={register('minimumInvestment')}
            error={errors.minimumInvestment?.message}
            disabled={isSubmitting}
            inputMode="decimal"
            placeholder="0.00"
          />
          <FormInput
            label="Investimento máximo (R$)"
            register={register('maximumInvestment')}
            error={errors.maximumInvestment?.message}
            disabled={isSubmitting}
            inputMode="decimal"
            placeholder="0.00"
          />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-foreground">
          Taxas iniciais
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <FormInput
            label="Taxa de franquia (R$)"
            register={register('franchiseFee')}
            error={errors.franchiseFee?.message}
            disabled={isSubmitting}
            inputMode="decimal"
            placeholder="0.00"
          />
          <FormInput
            label="Capital de instalação (R$)"
            register={register('setupCapital')}
            error={errors.setupCapital?.message}
            disabled={isSubmitting}
            inputMode="decimal"
            placeholder="0.00"
          />
          <FormInput
            label="Capital de giro (R$)"
            register={register('workingCapital')}
            error={errors.workingCapital?.message}
            disabled={isSubmitting}
            inputMode="decimal"
            placeholder="0.00"
          />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-foreground">
          Taxas recorrentes
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormInput
            label="Royalties (%)"
            register={register('royalties')}
            error={errors.royalties?.message}
            disabled={isSubmitting}
            inputMode="decimal"
            placeholder="0.00"
          />
          <FormSelect
            label="Base de cálculo de royalties"
            register={register('calculationBaseRoyaltie')}
            error={errors.calculationBaseRoyaltie?.message}
            disabled={isSubmitting}
            options={CALCULATION_BASE_OPTIONS}
          />
          <FormInput
            label="Fundo de propaganda (%)"
            register={register('advertisingFee')}
            error={errors.advertisingFee?.message}
            disabled={isSubmitting}
            inputMode="decimal"
            placeholder="0.00"
          />
          <FormSelect
            label="Base de cálculo de propaganda"
            register={register('calculationBaseAdFee')}
            error={errors.calculationBaseAdFee?.message}
            disabled={isSubmitting}
            options={CALCULATION_BASE_OPTIONS}
          />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-foreground">
          Retorno esperado
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <FormInput
            label="ROI mínimo (meses)"
            register={register('minimumReturnOnInvestment')}
            error={errors.minimumReturnOnInvestment?.message}
            disabled={isSubmitting}
            inputMode="numeric"
            placeholder="12"
          />
          <FormInput
            label="ROI máximo (meses)"
            register={register('maximumReturnOnInvestment')}
            error={errors.maximumReturnOnInvestment?.message}
            disabled={isSubmitting}
            inputMode="numeric"
            placeholder="24"
          />
          <FormInput
            label="Faturamento médio mensal (R$)"
            register={register('averageMonthlyRevenue')}
            error={errors.averageMonthlyRevenue?.message}
            disabled={isSubmitting}
            inputMode="decimal"
            placeholder="0.00"
          />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Operação</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormInput
            label="Área da loja (m²)"
            register={register('storeArea')}
            error={errors.storeArea?.message}
            disabled={isSubmitting}
            inputMode="numeric"
            placeholder="50"
          />
        </div>
      </section>

      <div className="flex items-center justify-end gap-3 pt-2 border-t border-border/50">
        <p className="text-xs text-muted-foreground mr-auto">
          {isDirty ? 'Alterações não salvas' : 'Nenhuma alteração pendente'}
        </p>
        <RoundedButton
          text="Salvar alterações"
          loadingText="Salvando..."
          loading={isSubmitting}
          disabled={isSubmitting || !isDirty}
          type="submit"
          color="#E25E3E"
          hoverColor="#c04e2e"
          textColor="#FFFFFF"
          hoverTextColor="#FFFFFF"
        />
      </div>
    </form>
  )
}
