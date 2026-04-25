'use client'

import Image from 'next/image'
import { useState } from 'react'
import { Clock } from 'lucide-react'
import { FranchisorRequest } from '@/src/schemas/users/FranchisorRequest'
import { useCancelMyFranchisorRequest } from '@/src/hooks/users/useFranchisorRequest'
import ModalConfirmation from '@/src/components/ui/ModalConfirmation'

interface ClaimCardProps {
  request: FranchisorRequest
}

export default function ClaimCard({ request }: ClaimCardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const cancelMutation = useCancelMyFranchisorRequest()

  if (!request.franchise) return null

  const franchise = request.franchise
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
  const logoSrc = franchise.logoUrl
    ? franchise.logoUrl.startsWith('http')
      ? franchise.logoUrl
      : `${apiUrl}${franchise.logoUrl}`
    : null

  const handleConfirmCancel = () => {
    cancelMutation.mutate(undefined, {
      onSuccess: () => setIsModalOpen(false),
    })
  }

  const handleCloseModal = () => {
    if (!cancelMutation.isPending) setIsModalOpen(false)
  }

  return (
    <>
      <div className="bg-white rounded-2xl border border-border/50 p-5 shadow-sm">
        <div className="flex items-start gap-4 mb-4">
          <div className="w-16 h-16 bg-white rounded-[12px] border border-border/50 flex items-center justify-center shrink-0 p-3">
            {logoSrc ? (
              <Image
                src={logoSrc}
                alt={franchise.name}
                width={64}
                height={64}
                className="object-contain w-full h-full"
                unoptimized
              />
            ) : (
              <span className="text-3xl" aria-hidden="true">
                🏢
              </span>
            )}
          </div>

          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-semibold text-foreground truncate">
              {franchise.name}
            </h2>
          </div>

          <div className="flex flex-col sm:items-end items-start gap-1.5 shrink-0">
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="text-sm text-gray-600 hover:underline cursor-pointer"
            >
              Cancelar reivindicação
            </button>
          </div>
        </div>

        <div
          className="flex items-start gap-3 rounded-xl border p-4 bg-amber-50 border-amber-200"
          role="status"
          aria-live="polite"
        >
          <Clock
            className="h-5 w-5 shrink-0 mt-0.5 text-amber-600"
            aria-hidden="true"
          />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-amber-900">
              Em análise pela equipe
            </p>
            <p className="text-sm mt-0.5 text-amber-800">
              Sua reivindicação de {franchise.name} está aguardando aprovação.
              Você será notificado por email.
            </p>
          </div>
        </div>
      </div>

      <ModalConfirmation
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        onConfirm={handleConfirmCancel}
        isLoading={cancelMutation.isPending}
        action="cancelar a reivindicação"
        text={`Tem certeza que deseja cancelar a reivindicação de ${franchise.name}? Esta ação não pode ser desfeita.`}
        buttonText="Sim, cancelar"
      />
    </>
  )
}
