'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Plus, Search, X } from 'lucide-react'
import ModeSelectorCard from '@/src/components/ui/ModeSelectorCard'
import FormInput from '@/src/components/ui/FormInput'
import FormSelect from '@/src/components/ui/FormSelect'
import FormTextarea from '@/src/components/ui/FormTextarea'
import RoundedButton from '@/src/components/ui/RoundedButton'
import { useSubmitFranchiseRequest } from '@/src/hooks/franchises/useSubmitFranchiseRequest'
import { franchiseQueries } from '@/src/queries/franchises'
import {
  FranchisorRequestFormSchema,
  type FranchisorRequestFormInput,
} from '@/src/schemas/users/FranchisorRequest'

interface CreateAdditionalFranchiseFormProps {
  open: boolean
  onClose: () => void
  onSuccess?: () => void
}

/**
 * Modal unificado de cadastro/reivindicação de franquia.
 *
 * Suporta 2 modos:
 * - NEW: cadastra nova marca (streamName obrigatório)
 * - EXISTING: reivindica marca existente no banco (franchiseId + claimReason obrigatórios)
 *
 * O hook useSubmitFranchiseRequest decide internamente qual endpoint backend chamar
 * baseado na role do user e no mode selecionado.
 */
export default function CreateAdditionalFranchiseForm({
  open,
  onClose,
  onSuccess,
}: CreateAdditionalFranchiseFormProps) {
  const mutation = useSubmitFranchiseRequest()

  const { data: availableFranchises = [] } = useQuery(
    franchiseQueries.availableOptions(),
  )

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FranchisorRequestFormInput>({
    resolver: zodResolver(FranchisorRequestFormSchema),
    defaultValues: {
      mode: undefined,
      streamName: '',
      franchiseId: '',
      claimReason: '',
    },
  })

  const mode = watch('mode')
  const isSubmitting = mutation.isPending

  const onSubmit = (data: FranchisorRequestFormInput) => {
    mutation.mutate(
      {
        mode: data.mode,
        streamName: data.streamName || undefined,
        franchiseId: data.franchiseId || undefined,
        claimReason: data.claimReason || undefined,
      },
      {
        onSuccess: () => {
          toast.success(
            data.mode === 'NEW'
              ? 'Marca cadastrada! Aguardando aprovação.'
              : 'Reivindicação enviada! Nossa equipe vai analisar.',
          )
          reset()
          onSuccess?.()
          onClose()
        },
        onError: (err: Error) => {
          toast.error(err.message || 'Erro ao enviar. Tente novamente.')
        },
      },
    )
  }

  const handleClose = () => {
    if (isSubmitting) return
    reset()
    onClose()
  }

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={handleClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-franchise-title"
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Sticky header */}
        <div className="sticky top-0 bg-white border-b border-gray-100 p-5 flex items-center justify-between z-10">
          <h2
            id="create-franchise-title"
            className="text-lg font-semibold text-gray-900"
          >
            Cadastrar franquia
          </h2>
          <button
            type="button"
            onClick={handleClose}
            disabled={isSubmitting}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
            aria-label="Fechar"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="p-5 space-y-5">
          {/* Mode selector */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-3">
              O que você quer fazer?
            </label>
            <ModeSelectorCard<'NEW' | 'EXISTING'>
              name="Tipo de cadastro"
              value={(mode as 'NEW' | 'EXISTING') ?? null}
              onChange={(v) =>
                setValue('mode', v, { shouldValidate: true, shouldDirty: true })
              }
              disabled={isSubmitting}
              options={[
                {
                  value: 'NEW',
                  label: 'Cadastrar nova marca',
                  description: 'Minha marca ainda não está no site',
                  icon: <Plus className="w-5 h-5" />,
                },
                {
                  value: 'EXISTING',
                  label: 'Reivindicar marca existente',
                  description: 'Minha marca já aparece aqui',
                  icon: <Search className="w-5 h-5" />,
                },
              ]}
            />
            {errors.mode && (
              <p className="text-red-500 text-sm mt-2">{errors.mode.message}</p>
            )}
          </div>

          {/* NEW fields */}
          {mode === 'NEW' && (
            <div className="space-y-3">
              <FormInput
                label="Nome da marca"
                register={register('streamName')}
                error={errors.streamName?.message}
                placeholder="Ex: Pizza do Jorge"
                disabled={isSubmitting}
                autoFocus
              />
              <p className="text-sm text-gray-500">
                Após aprovação, você poderá completar descrição, logo, segmento
                e outros dados pelo painel.
              </p>
            </div>
          )}

          {/* EXISTING fields */}
          {mode === 'EXISTING' && (
            <div className="space-y-4">
              <div>
                <FormSelect
                  label="Qual é a sua marca?"
                  register={register('franchiseId')}
                  error={errors.franchiseId?.message}
                  options={availableFranchises}
                  placeholder="Selecione sua franquia"
                  disabled={isSubmitting}
                />
                <p className="text-sm text-gray-500 mt-2">
                  Não encontrou sua marca?{' '}
                  <a
                    href="mailto:contato@mercadofranquia.com.br?subject=Reivindicação de franquia não listada"
                    className="text-[#E25E3E] hover:underline"
                  >
                    Fale com nossa equipe
                  </a>
                  .
                </p>
              </div>

              <FormTextarea
                label="Por que você é o dono desta marca?"
                register={register('claimReason')}
                error={errors.claimReason?.message}
                placeholder="Ex: Sou fundador da marca desde 2015. Posso enviar documentos que comprovem."
                rows={4}
                disabled={isSubmitting}
                showCharacterCount
                maxCharacterCount={1000}
              />
            </div>
          )}

          {/* Actions */}
          {mode && (
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={handleClose}
                disabled={isSubmitting}
                className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors disabled:opacity-50"
              >
                Cancelar
              </button>
              <RoundedButton
                text="Enviar"
                loadingText="Enviando..."
                loading={isSubmitting}
                disabled={isSubmitting}
                type="submit"
                color="#E25E3E"
                hoverColor="#c04e2e"
                textColor="#FFFFFF"
                hoverTextColor="#FFFFFF"
              />
            </div>
          )}
        </form>
      </div>
    </div>
  )
}
