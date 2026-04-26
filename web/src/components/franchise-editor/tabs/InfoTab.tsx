'use client'

import { useMemo } from 'react'
import { useFieldArray, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Info, Plus, Trash2 } from 'lucide-react'
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
    tagline: f.tagline ?? '',
    idealFranchiseeProfile: f.idealFranchiseeProfile ?? '',
    differentials: f.differentials ?? [],
    processSteps: f.processSteps ?? [],
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
    control,
    formState: { errors, dirtyFields, isDirty },
  } = useForm<FranchiseEditorInfoFormInput>({
    resolver: zodResolver(FranchiseEditorInfoFormSchema),
    defaultValues: defaults,
  })

  const isAbfAssociated = watch('isAbfAssociated')

  const differentialsArray = useFieldArray({
    control,
    name: 'differentials' as never,
  })
  const processStepsArray = useFieldArray({
    control,
    name: 'processSteps',
  })

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
        <h2 className="text-lg font-semibold text-foreground">
          Apresentação na landing pública
        </h2>
        <p className="text-xs text-muted-foreground -mt-2">
          Informações que aparecem na sua página pública pra investidores. Tudo
          é opcional — blocos sem preenchimento somem da página.
        </p>

        <div>
          <FormInput
            label="Tagline"
            register={register('tagline')}
            error={errors.tagline?.message}
            disabled={isSubmitting}
            placeholder="Ex: Leve a experiência do verdadeiro gelato pro Brasil"
            maxLength={200}
          />
          <p className="text-xs text-muted-foreground mt-1">
            Aparece abaixo do nome no Hero. Frase curta de impacto.
          </p>
        </div>

        <FormTextarea
          label="Perfil ideal do franqueado"
          register={register('idealFranchiseeProfile')}
          error={errors.idealFranchiseeProfile?.message}
          disabled={isSubmitting}
          rows={4}
          placeholder="Ex: Empreendedor com perfil de gestão e dedicação ao negócio. Não é necessário experiência prévia em alimentação."
          showCharacterCount
          maxCharacterCount={10000}
        />
        <p className="text-xs text-muted-foreground -mt-2">
          Texto livre — descreva o perfil que dá certo na sua rede.
        </p>

        {/* Diferenciais — lista editavel de strings */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-foreground">
              Diferenciais
            </label>
            <button
              type="button"
              onClick={() =>
                (differentialsArray.append as (v: string) => void)('')
              }
              disabled={isSubmitting || differentialsArray.fields.length >= 6}
              className="text-xs flex items-center gap-1 text-primary hover:opacity-80 disabled:opacity-40"
            >
              <Plus className="h-3.5 w-3.5" /> Adicionar
            </button>
          </div>
          {differentialsArray.fields.length === 0 && (
            <p className="text-xs text-muted-foreground italic">
              Nenhum diferencial cadastrado. Ex: &ldquo;Produto premium difícil
              de substituir&rdquo;, &ldquo;Cardápio inclusivo&rdquo;.
            </p>
          )}
          <ul className="space-y-2">
            {differentialsArray.fields.map((field, i) => (
              <li key={field.id} className="flex items-start gap-2">
                <input
                  {...register(`differentials.${i}` as const)}
                  disabled={isSubmitting}
                  placeholder="Ex: Produto premium difícil de substituir"
                  maxLength={200}
                  className="flex-1 px-3 py-2 text-sm border border-input rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
                <button
                  type="button"
                  onClick={() => differentialsArray.remove(i)}
                  disabled={isSubmitting}
                  aria-label="Remover diferencial"
                  className="p-2 text-muted-foreground hover:text-destructive disabled:opacity-40"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
          {errors.differentials && (
            <p className="text-xs text-destructive">
              {errors.differentials.message ||
                'Verifique os diferenciais cadastrados.'}
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            Máximo 6 itens. Cada um até 200 caracteres.
          </p>
        </div>

        {/* Process steps — Como funciona */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-foreground">
              Etapas (&ldquo;Como funciona&rdquo;)
            </label>
            <button
              type="button"
              onClick={() =>
                processStepsArray.append({ title: '', description: '' })
              }
              disabled={isSubmitting || processStepsArray.fields.length >= 8}
              className="text-xs flex items-center gap-1 text-primary hover:opacity-80 disabled:opacity-40"
            >
              <Plus className="h-3.5 w-3.5" /> Adicionar etapa
            </button>
          </div>
          {processStepsArray.fields.length === 0 && (
            <p className="text-xs text-muted-foreground italic">
              Nenhuma etapa cadastrada. Ex: 1. Pré-qualificação · 2. Análise da
              COF · 3. Contrato e ponto comercial.
            </p>
          )}
          <ol className="space-y-3">
            {processStepsArray.fields.map((field, i) => (
              <li
                key={field.id}
                className="border border-border rounded-md p-3 bg-muted/30 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">
                    Etapa {i + 1}
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => i > 0 && processStepsArray.move(i, i - 1)}
                      disabled={isSubmitting || i === 0}
                      aria-label="Mover pra cima"
                      className="px-2 py-1 text-xs text-muted-foreground hover:text-foreground disabled:opacity-30"
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        i < processStepsArray.fields.length - 1 &&
                        processStepsArray.move(i, i + 1)
                      }
                      disabled={
                        isSubmitting ||
                        i === processStepsArray.fields.length - 1
                      }
                      aria-label="Mover pra baixo"
                      className="px-2 py-1 text-xs text-muted-foreground hover:text-foreground disabled:opacity-30"
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      onClick={() => processStepsArray.remove(i)}
                      disabled={isSubmitting}
                      aria-label="Remover etapa"
                      className="p-1 text-muted-foreground hover:text-destructive disabled:opacity-40"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <input
                  {...register(`processSteps.${i}.title` as const)}
                  disabled={isSubmitting}
                  placeholder="Título (ex: Pré-qualificação)"
                  maxLength={200}
                  className="w-full px-3 py-2 text-sm font-medium border border-input rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
                {errors.processSteps?.[i]?.title && (
                  <p className="text-xs text-destructive">
                    {errors.processSteps[i]?.title?.message}
                  </p>
                )}
                <textarea
                  {...register(`processSteps.${i}.description` as const)}
                  disabled={isSubmitting}
                  rows={2}
                  placeholder="Descrição curta (ex: Apresentação e ficha inicial)"
                  maxLength={500}
                  className="w-full px-3 py-2 text-sm border border-input rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
                />
                {errors.processSteps?.[i]?.description && (
                  <p className="text-xs text-destructive">
                    {errors.processSteps[i]?.description?.message}
                  </p>
                )}
              </li>
            ))}
          </ol>
          <p className="text-xs text-muted-foreground">
            Máximo 8 etapas. Use as setas pra reordenar.
          </p>
        </div>
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
