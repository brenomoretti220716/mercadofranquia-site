'use client'

import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { useFranchises } from '@/src/hooks/franchises/useFranchises'
import { franchiseKeys } from '@/src/queries/franchises'
import {
  FranchisorRequestFormInput,
  FranchisorRequestFormSchema,
} from '@/src/schemas/users/FranchisorRequest'
import { createFranchisorRequest } from '@/src/services/users'
import {
  getClientAuthCookie,
  setClientAuthCookie,
} from '@/src/utils/clientCookie'
import { formatErrorMessage } from '@/src/utils/errorHandlers'
import FormInput from '@/src/components/ui/FormInput'
import FormSelect from '@/src/components/ui/FormSelect'
import FormTextarea from '@/src/components/ui/FormTextarea'
import ModeSelectorCard from '@/src/components/ui/ModeSelectorCard'
import RoundedButton from '@/src/components/ui/RoundedButton'

interface FranchisorStep3Props {
  onSuccess: () => void
}

export default function FranchisorStep3({ onSuccess }: FranchisorStep3Props) {
  const queryClient = useQueryClient()
  const { franchiseOptions } = useFranchises()

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FranchisorRequestFormInput>({
    resolver: zodResolver(FranchisorRequestFormSchema),
    defaultValues: {
      mode: 'NEW',
      streamName: '',
      franchiseId: '',
      claimReason: '',
    },
  })

  const mode = watch('mode')

  const submitMutation = useMutation({
    mutationFn: async (data: FranchisorRequestFormInput) => {
      const token = getClientAuthCookie()
      if (!token) throw new Error('Sessão expirada. Recarregue a página.')

      return createFranchisorRequest(token, {
        mode: data.mode,
        streamName: data.mode === 'NEW' ? data.streamName : undefined,
        franchiseId: data.mode === 'EXISTING' ? data.franchiseId : undefined,
        claimReason: data.mode === 'EXISTING' ? data.claimReason : undefined,
      })
    },
    onSuccess: (data) => {
      if (data.access_token) {
        setClientAuthCookie(data.access_token)
      }
      queryClient.invalidateQueries({ queryKey: franchiseKeys.myFranchises() })
      queryClient.invalidateQueries({
        queryKey: ['franchisor-request', 'my-request'],
      })
      toast.success('Solicitação enviada! Aguardando aprovação.')
      onSuccess()
    },
    onError: (error) => {
      toast.error(
        formatErrorMessage(
          error,
          'Erro ao enviar solicitação. Tente novamente.',
        ),
      )
    },
  })

  const loading = submitMutation.isPending

  return (
    <form
      onSubmit={handleSubmit((data) => submitMutation.mutate(data))}
      className="space-y-5 w-full"
      noValidate
    >
      <div>
        <label className="block text-sm font-medium text-gray-900 mb-3">
          Sua marca já aparece no Mercado Franquia?
        </label>
        <ModeSelectorCard<'NEW' | 'EXISTING'>
          name="Tipo de cadastro"
          value={mode}
          onChange={(v) =>
            setValue('mode', v, { shouldValidate: true, shouldDirty: true })
          }
          disabled={loading}
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

      {mode === 'NEW' && (
        <div className="space-y-3">
          <FormInput
            label="Nome da marca"
            register={register('streamName')}
            error={errors.streamName?.message}
            placeholder="Ex: Pizza do Jorge"
            disabled={loading}
            autoFocus
          />
          <p className="text-sm text-gray-500">
            Após aprovação, você poderá completar descrição, logo, segmento e
            outros dados pelo painel.
          </p>
        </div>
      )}

      {mode === 'EXISTING' && (
        <div className="space-y-4">
          <div>
            <FormSelect
              label="Qual é a sua marca?"
              register={register('franchiseId')}
              error={errors.franchiseId?.message}
              options={franchiseOptions}
              placeholder="Selecione sua franquia"
              disabled={loading}
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
            disabled={loading}
            showCharacterCount
            maxCharacterCount={1000}
          />
        </div>
      )}

      <div className="grid w-full pt-2">
        <RoundedButton
          color="#000000"
          hoverColor="hsl(10 79% 57%)"
          text={loading ? 'Enviando...' : 'Cadastrar marca'}
          textColor="white"
          hoverTextColor="white"
          disabled={loading}
          loading={loading}
          loadingText="Enviando..."
          type="submit"
        />
      </div>
    </form>
  )
}
