'use client'

import { useCallback, useState } from 'react'
import { StepOneRegistrationInput } from '@/src/schemas/users/auth'
import { FranchisorStepTwoInput } from '@/src/schemas/users/franchisorAuth'
import { useFranchisorStepOneMutation } from '@/src/hooks/users/useFranchisorRegisterMutations'
import type { CreateFranchisorRequestResponse } from '@/src/services/users'
import FranchisorStep1 from './franchisorSteps/FranchisorStep1'
import FranchisorStep2 from './franchisorSteps/FranchisorStep2'
import FranchisorStep3 from './franchisorSteps/FranchisorStep3'

type Step = 'step1' | 'step2' | 'step3'

const STEPS: { id: Step; label: string; number: number }[] = [
  { id: 'step1', label: 'Credenciais', number: 1 },
  { id: 'step2', label: 'Perfil', number: 2 },
  { id: 'step3', label: 'Marca', number: 3 },
]

function redirectTo(path: string) {
  setTimeout(() => {
    window.location.href = path
  }, 1500)
}

export default function FranchisorRegisterFlow() {
  const [currentStep, setCurrentStep] = useState<Step>('step1')
  const [step1Data, setStep1Data] = useState<StepOneRegistrationInput | null>(
    null,
  )
  const [step2Data, setStep2Data] = useState<FranchisorStepTwoInput | null>(
    null,
  )

  const stepOneMutation = useFranchisorStepOneMutation({
    onSuccess: () => setCurrentStep('step3'),
  })

  const handleStep1Submit = useCallback((data: StepOneRegistrationInput) => {
    setStep1Data(data)
    setCurrentStep('step2')
  }, [])

  const handleStep2Submit = useCallback(
    (data: FranchisorStepTwoInput) => {
      if (!step1Data) return
      setStep2Data(data)
      stepOneMutation.mutate({ ...step1Data, ...data })
    },
    [step1Data, stepOneMutation],
  )

  const handleStep3Success = useCallback(
    (data: CreateFranchisorRequestResponse) => {
      const req = data.request
      if (req.mode === 'NEW' && req.franchise?.slug) {
        redirectTo(`/franqueador/franquias/${req.franchise.slug}/editar`)
      } else {
        redirectTo('/franqueador/minhas-franquias')
      }
    },
    [],
  )

  const handleBack = useCallback(() => {
    if (currentStep === 'step2') setCurrentStep('step1')
  }, [currentStep])

  const currentIndex = STEPS.findIndex((s) => s.id === currentStep)

  const { title, subtitle } = (() => {
    switch (currentStep) {
      case 'step1':
        return {
          title: 'Anuncie sua franquia',
          subtitle: 'Comece criando suas credenciais de acesso',
        }
      case 'step2':
        return {
          title: 'Complete seu perfil',
          subtitle: 'Precisamos de alguns dados sobre você',
        }
      case 'step3':
        return {
          title: 'Cadastre sua marca',
          subtitle:
            'Escolha se vai cadastrar uma marca nova ou reivindicar uma existente',
        }
    }
  })()

  return (
    <div className="w-full">
      <div className="flex justify-center items-center gap-2 mb-4 sm:mb-6">
        {STEPS.map((step, index) => (
          <div key={step.id} className="flex items-center">
            <div
              className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-semibold transition-colors ${
                index <= currentIndex
                  ? 'bg-primary text-white'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              {step.number}
            </div>
            {index < STEPS.length - 1 && (
              <div
                className={`w-8 sm:w-12 h-0.5 mx-1 transition-colors ${
                  index < currentIndex ? 'bg-primary' : 'bg-muted'
                }`}
              />
            )}
          </div>
        ))}
      </div>

      <div className="mb-4 sm:mb-6 text-center">
        <h1 className="text-xl sm:text-2xl font-bold text-foreground mb-2">
          {title}
        </h1>
        <p className="text-sm sm:text-base text-muted-foreground">{subtitle}</p>
      </div>

      {currentStep === 'step1' && (
        <FranchisorStep1
          defaultValues={step1Data ?? undefined}
          onSubmit={handleStep1Submit}
        />
      )}

      {currentStep === 'step2' && (
        <FranchisorStep2
          defaultValues={step2Data ?? undefined}
          loading={stepOneMutation.isPending}
          onSubmit={handleStep2Submit}
          onBack={handleBack}
        />
      )}

      {currentStep === 'step3' && (
        <FranchisorStep3 onSuccess={handleStep3Success} />
      )}
    </div>
  )
}
