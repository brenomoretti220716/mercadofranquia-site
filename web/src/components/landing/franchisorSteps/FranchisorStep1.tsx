'use client'

import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import {
  StepOneRegistrationInput,
  StepOneRegistrationSchema,
} from '@/src/schemas/users/auth'
import MailIcon from '@/src/components/icons/emailIcon'
import FormInput from '@/src/components/ui/FormInput'
import PasswordInput from '@/src/components/ui/PasswordInput'
import RoundedButton from '@/src/components/ui/RoundedButton'

interface FranchisorStep1Props {
  defaultValues?: Partial<StepOneRegistrationInput>
  onSubmit: (data: StepOneRegistrationInput) => void
}

export default function FranchisorStep1({
  defaultValues,
  onSubmit,
}: FranchisorStep1Props) {
  const form = useForm<StepOneRegistrationInput>({
    resolver: zodResolver(StepOneRegistrationSchema),
    defaultValues: {
      email: defaultValues?.email ?? '',
      password: defaultValues?.password ?? '',
      confirmPassword: defaultValues?.confirmPassword ?? '',
    },
  })

  return (
    <form
      className="space-y-4 w-full px-0.5"
      onSubmit={form.handleSubmit(onSubmit)}
      noValidate
    >
      <FormInput
        label="E-mail"
        id="email"
        type="email"
        placeholder="seu@email.com"
        leftIcon={<MailIcon width={20} height={20} color="#747473" />}
        error={form.formState.errors.email?.message}
        register={form.register('email')}
      />

      <PasswordInput
        label="Senha"
        id="password"
        error={form.formState.errors.password?.message}
        register={form.register('password')}
      />

      <PasswordInput
        label="Confirme sua senha"
        id="confirmPassword"
        error={form.formState.errors.confirmPassword?.message}
        register={form.register('confirmPassword')}
      />

      <div className="text-left mt-2">
        <p className="text-xs text-muted-foreground mb-1">
          A senha deve conter:
        </p>
        <ul className="text-xs text-muted-foreground list-disc list-inside space-y-0.5">
          <li>Mínimo de 6 caracteres</li>
          <li>Pelo menos uma letra maiúscula</li>
          <li>Pelo menos um número</li>
        </ul>
      </div>

      <div className="grid w-full mt-6">
        <RoundedButton
          color="hsl(240 24% 12%)"
          hoverColor="hsl(10 79% 57%)"
          text="Continuar"
          textColor="white"
          hoverTextColor="white"
          type="submit"
        />
      </div>
    </form>
  )
}
