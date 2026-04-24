'use client'

import { useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Info } from 'lucide-react'
import FormInput from '@/src/components/ui/FormInput'
import FormSelect from '@/src/components/ui/FormSelect'
import FormTextarea from '@/src/components/ui/FormTextarea'
import RoundedButton from '@/src/components/ui/RoundedButton'
import type { Franchise } from '@/src/schemas/franchises/Franchise'
import {
  FranchiseEditorInfoFormSchema,
  normalizeFranchiseEditorPayload,
  type FranchiseEditorInfoFormInput,
} from '@/src/schemas/franchises/FranchiseEditor'
import { useUpdateFranchisorFranchise } from '@/src/hooks/franchises/useFranchisorFranchiseMutations'

const UNITS_EVOLUTION_OPTIONS = [
  { value: '', label: 'Selecione...' },
  { value: 'UP', label: 'Em crescimento' },
  { value: 'MAINTAIN', label: 'Estável' },
  { value: 'DOWN', label: 'Em retração' },
]

const BR_STATES = [
  'AC',
  'AL',
  'AM',
  'AP',
  'BA',
  'CE',
  'DF',
  'ES',
  'GO',
  'MA',
  'MG',
  'MS',
  'MT',
  'PA',
  'PB',
  'PE',
  'PI',
  'PR',
  'RJ',
  'RN',
  'RO',
  'RR',
  'RS',
  'SC',
  'SE',
  'SP',
  'TO',
]

const STATE_OPTIONS = [
  { value: '', label: 'Selecione o estado' },
  ...BR_STATES.map((uf) => ({ value: uf, label: uf })),
]

function franchiseToFormDefaults(f: Franchise): FranchiseEditorInfoFormInput {
  return {
    name: f.name ?? '',
    description: f.description ?? '',
    detailedDescription: f.detailedDescription ?? '',
    segment: f.segment ?? '',
    subsegment: f.subsegment ?? '',
    businessType: f.businessType ?? '',
    headquarter: f.headquarter ?? '',
    headquarterState: f.headquarterState ?? '',
    totalUnits: typeof f.totalUnits === 'number' ? String(f.totalUnits) : '',
    totalUnitsInBrazil:
      typeof f.totalUnitsInBrazil === 'number'
        ? String(f.totalUnitsInBrazil)
        : '',
    unitsEvolution: f.unitsEvolution ?? '',
    brandFoundationYear:
      typeof f.brandFoundationYear === 'number'
        ? String(f.brandFoundationYear)
        : '',
    franchiseStartYear:
      typeof f.franchiseStartYear === 'number'
        ? String(f.franchiseStartYear)
        : '',
    abfSince: typeof f.abfSince === 'number' ? String(f.abfSince) : '',
    isAbfAssociated:
      typeof f.isAbfAssociated === 'boolean' ? f.isAbfAssociated : undefined,
    contactPhone: f.contact?.phone ?? '',
    contactEmail: f.contact?.email ?? '',
    contactWebsite: f.contact?.website ?? '',
  }
}

interface InfoTabProps {
  franchise: Franchise
  token: string
  userRole: string
}

export default function InfoTab({ franchise, token, userRole }: InfoTabProps) {
  const mutation = useUpdateFranchisorFranchise()
  const isApproved = franchise.status === 'APPROVED'
  const isAdmin = userRole === 'ADMIN'
  const nameLocked = isApproved && !isAdmin

  const defaults = useMemo(
    () => franchiseToFormDefaults(franchise),
    [franchise],
  )

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, dirtyFields, isDirty },
  } = useForm<FranchiseEditorInfoFormInput>({
    resolver: zodResolver(FranchiseEditorInfoFormSchema),
    defaultValues: defaults,
  })

  const isAbfAssociated = watch('isAbfAssociated')

  const onSubmit = (data: FranchiseEditorInfoFormInput) => {
    const payload = normalizeFranchiseEditorPayload(
      data,
      dirtyFields as Partial<
        Record<keyof FranchiseEditorInfoFormInput, boolean>
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
          reset(franchiseToFormDefaults(fresh))
        },
      },
    )
  }

  const isSubmitting = mutation.isPending

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-foreground">
          Identidade da marca
        </h2>

        <div>
          <FormInput
            label="Nome da marca"
            register={register('name')}
            error={errors.name?.message}
            disabled={isSubmitting || nameLocked}
            placeholder="Ex: Pizza do Jorge"
          />
          {nameLocked && (
            <p className="text-xs text-muted-foreground mt-1 flex items-start gap-1.5">
              <Info
                className="h-3.5 w-3.5 mt-0.5 shrink-0"
                aria-hidden="true"
              />
              O nome não pode ser alterado após a aprovação. Fale com o admin se
              precisar mudar.
            </p>
          )}
        </div>

        <FormTextarea
          label="Descrição curta"
          register={register('description')}
          error={errors.description?.message}
          disabled={isSubmitting}
          rows={2}
          placeholder="Uma frase que resume sua franquia"
          showCharacterCount
          maxCharacterCount={1000}
        />

        <FormTextarea
          label="Descrição detalhada"
          register={register('detailedDescription')}
          error={errors.detailedDescription?.message}
          disabled={isSubmitting}
          rows={6}
          placeholder="Conte mais sobre o modelo de negócio, história, diferenciais..."
          showCharacterCount
          maxCharacterCount={10000}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Classificação</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormInput
            label="Segmento"
            register={register('segment')}
            error={errors.segment?.message}
            disabled={isSubmitting}
            placeholder="Ex: Alimentação"
          />
          <FormInput
            label="Subsegmento"
            register={register('subsegment')}
            error={errors.subsegment?.message}
            disabled={isSubmitting}
            placeholder="Ex: Pizzarias"
          />
          <FormInput
            label="Tipo de negócio"
            register={register('businessType')}
            error={errors.businessType?.message}
            disabled={isSubmitting}
            placeholder="Ex: Loja física, Food Truck, Delivery"
          />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-foreground">
          Localização e unidades
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormInput
            label="Cidade sede"
            register={register('headquarter')}
            error={errors.headquarter?.message}
            disabled={isSubmitting}
            placeholder="Ex: São Paulo"
          />
          <FormSelect
            label="Estado sede (UF)"
            register={register('headquarterState')}
            error={errors.headquarterState?.message}
            disabled={isSubmitting}
            options={STATE_OPTIONS}
          />
          <FormInput
            label="Unidades totais"
            register={register('totalUnits')}
            error={errors.totalUnits?.message}
            disabled={isSubmitting}
            inputMode="numeric"
            placeholder="0"
          />
          <FormInput
            label="Unidades no Brasil"
            register={register('totalUnitsInBrazil')}
            error={errors.totalUnitsInBrazil?.message}
            disabled={isSubmitting}
            inputMode="numeric"
            placeholder="0"
          />
          <FormSelect
            label="Evolução das unidades"
            register={register('unitsEvolution')}
            error={errors.unitsEvolution?.message}
            disabled={isSubmitting}
            options={UNITS_EVOLUTION_OPTIONS}
          />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-foreground">
          Histórico e associação
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormInput
            label="Ano de fundação da marca"
            register={register('brandFoundationYear')}
            error={errors.brandFoundationYear?.message}
            disabled={isSubmitting}
            inputMode="numeric"
            placeholder="Ex: 1995"
          />
          <FormInput
            label="Começou a franquear em"
            register={register('franchiseStartYear')}
            error={errors.franchiseStartYear?.message}
            disabled={isSubmitting}
            inputMode="numeric"
            placeholder="Ex: 2001"
          />
        </div>

        <label className="flex items-center gap-2 text-sm text-foreground select-none">
          <input
            type="checkbox"
            {...register('isAbfAssociated')}
            disabled={isSubmitting}
            className="h-4 w-4 rounded border-input text-primary"
          />
          Associada à ABF
        </label>

        {isAbfAssociated ? (
          <FormInput
            label="Associada à ABF desde"
            register={register('abfSince')}
            error={errors.abfSince?.message}
            disabled={isSubmitting}
            inputMode="numeric"
            placeholder="Ex: 2010"
          />
        ) : null}
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Contato</h2>
        <p className="text-xs text-muted-foreground -mt-2">
          Preencha pra que seus leads tenham como entrar em contato. Você pode
          preencher parcialmente e completar depois.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormInput
            label="Telefone"
            register={register('contactPhone')}
            error={errors.contactPhone?.message}
            disabled={isSubmitting}
            placeholder="(11) 91234-5678"
          />
          <FormInput
            label="E-mail"
            register={register('contactEmail')}
            error={errors.contactEmail?.message}
            disabled={isSubmitting}
            type="email"
            placeholder="contato@suamarca.com.br"
          />
        </div>
        <FormInput
          label="Site"
          register={register('contactWebsite')}
          error={errors.contactWebsite?.message}
          disabled={isSubmitting}
          placeholder="https://suamarca.com.br"
        />
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
