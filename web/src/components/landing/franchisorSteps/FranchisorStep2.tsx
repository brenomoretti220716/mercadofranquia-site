'use client'

import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import {
  FranchisorStepTwoInput,
  FranchisorStepTwoSchema,
} from '@/src/schemas/users/franchisorAuth'
import PhoneIcon from '@/src/components/icons/phoneIcon'
import ProfileIcon from '@/src/components/icons/profileIcon'
import FormInput from '@/src/components/ui/FormInput'
import PhoneInput from '@/src/components/ui/PhoneInput'
import RoundedButton from '@/src/components/ui/RoundedButton'

interface FranchisorStep2Props {
  defaultValues?: Partial<FranchisorStepTwoInput>
  loading: boolean
  onSubmit: (data: FranchisorStepTwoInput) => void
  onBack: () => void
}

export default function FranchisorStep2({
  defaultValues,
  loading,
  onSubmit,
  onBack,
}: FranchisorStep2Props) {
  const form = useForm<FranchisorStepTwoInput>({
    resolver: zodResolver(FranchisorStepTwoSchema),
    defaultValues: {
      name: defaultValues?.name ?? '',
      phone: defaultValues?.phone ?? '',
      jobTitle: defaultValues?.jobTitle ?? '',
    },
  })

  return (
    <form
      className="space-y-4 w-full px-0.5"
      onSubmit={form.handleSubmit(onSubmit)}
      noValidate
    >
      <FormInput
        label="Nome completo"
        id="name"
        type="text"
        placeholder="Seu nome completo"
        leftIcon={<ProfileIcon width={20} height={20} color="#747473" />}
        error={form.formState.errors.name?.message}
        register={form.register('name')}
        disabled={loading}
      />

      <PhoneInput
        label="Número de celular"
        id="phone"
        placeholder="(11) 99999-9999"
        leftIcon={<PhoneIcon width={20} height={20} color="#747473" />}
        error={form.formState.errors.phone?.message}
        register={form.register('phone')}
        disabled={loading}
      />

      <FormInput
        label="Cargo na empresa"
        id="jobTitle"
        type="text"
        placeholder="Ex: CEO, Diretor de Expansão, Sócio-fundador"
        error={form.formState.errors.jobTitle?.message}
        register={form.register('jobTitle')}
        disabled={loading}
      />

      <div className="grid grid-cols-2 gap-3 mt-6">
        <RoundedButton
          color="#000000"
          hoverColor="hsl(10 79% 57%)"
          text="Voltar"
          textColor="white"
          hoverTextColor="white"
          onClick={onBack}
          type="button"
          disabled={loading}
        />
        <RoundedButton
          color="#000000"
          hoverColor="hsl(10 79% 57%)"
          text={loading ? 'Cadastrando...' : 'Continuar'}
          textColor="white"
          hoverTextColor="white"
          disabled={loading}
          type="submit"
        />
      </div>
    </form>
  )
}
