'use client'

import BaseModal from '@/src/components/ui/BaseModal'
import ModalConfirmation from '@/src/components/ui/ModalConfirmation'
import RoundedButton from '@/src/components/ui/RoundedButton'
import {
  useApproveFranchisorRequest,
  useRejectFranchisorRequest,
  useReopenFranchisorRequest,
} from '@/src/hooks/users/useFranchisorRequest'
import {
  FranchisorRequest,
  FranchisorRequestStatus,
} from '@/src/schemas/users/FranchisorRequest'
import { formatDateTimeToBrazilian } from '@/src/utils/dateFormatters'
import { formatErrorMessage } from '@/src/utils/errorHandlers'
import Image from 'next/image'
import { useState } from 'react'
import { toast } from 'sonner'

interface Props {
  isOpen: boolean
  onClose: () => void
  request: FranchisorRequest | null
  onSuccess: () => void
}

const statusColors = {
  [FranchisorRequestStatus.PENDING]: 'bg-yellow-100 text-yellow-800',
  [FranchisorRequestStatus.UNDER_REVIEW]: 'bg-blue-100 text-blue-800',
  [FranchisorRequestStatus.APPROVED]: 'bg-green-100 text-green-800',
  [FranchisorRequestStatus.REJECTED]: 'bg-red-100 text-red-800',
  [FranchisorRequestStatus.CANCELLED]: 'bg-gray-100 text-gray-800',
}

const statusLabels = {
  [FranchisorRequestStatus.PENDING]: 'Pendente',
  [FranchisorRequestStatus.UNDER_REVIEW]: 'Em Análise',
  [FranchisorRequestStatus.APPROVED]: 'Aprovado',
  [FranchisorRequestStatus.REJECTED]: 'Rejeitado',
  [FranchisorRequestStatus.CANCELLED]: 'Cancelada',
}

const modeLabels = {
  NEW: 'Marca nova',
  EXISTING: 'Reivindicação',
}

const modeColors = {
  NEW: 'bg-indigo-100 text-indigo-800',
  EXISTING: 'bg-purple-100 text-purple-800',
}

export default function FranchisorRequestModal({
  isOpen,
  onClose,
  request,
  onSuccess,
}: Props) {
  const [rejectionReason, setRejectionReason] = useState('')
  const [showApproveConfirmModal, setShowApproveConfirmModal] = useState(false)
  const [showRejectConfirmModal, setShowRejectConfirmModal] = useState(false)
  const [showReopenConfirmModal, setShowReopenConfirmModal] = useState(false)

  const approveMutation = useApproveFranchisorRequest()
  const rejectMutation = useRejectFranchisorRequest()
  const reopenMutation = useReopenFranchisorRequest()

  if (!request) return null

  const formatDate = formatDateTimeToBrazilian

  const handleApprove = () => {
    setShowApproveConfirmModal(true)
  }

  const confirmApprove = async () => {
    try {
      await approveMutation.mutateAsync(request.id)
      toast.success('Solicitação aprovada com sucesso!')
      setShowApproveConfirmModal(false)
      onSuccess()
      handleClose()
    } catch (error: unknown) {
      const message = formatErrorMessage(
        error,
        'Não foi possível aprovar a solicitação. Tente novamente.',
      )
      toast.error(message)
    }
  }

  const handleReject = () => {
    if (rejectionReason.trim().length < 10) {
      toast.error('Motivo da rejeição deve ter pelo menos 10 caracteres')
      return
    }
    setShowRejectConfirmModal(true)
  }

  const confirmReject = async () => {
    try {
      await rejectMutation.mutateAsync({
        requestId: request.id,
        data: { rejectionReason: rejectionReason.trim() },
      })
      toast.success('Solicitação rejeitada.')
      setShowRejectConfirmModal(false)
      onSuccess()
      handleClose()
    } catch (error: unknown) {
      const message = formatErrorMessage(
        error,
        'Não foi possível rejeitar a solicitação. Tente novamente.',
      )
      toast.error(message)
    }
  }

  const handleReopen = () => {
    setShowReopenConfirmModal(true)
  }

  const confirmReopen = async () => {
    try {
      await reopenMutation.mutateAsync(request.id)
      toast.success('Solicitação reaberta. Agora está pendente novamente.')
      setShowReopenConfirmModal(false)
      onSuccess()
      handleClose()
    } catch (error: unknown) {
      const message = formatErrorMessage(
        error,
        'Não foi possível reabrir a solicitação.',
      )
      toast.error(message)
    }
  }

  const handleClose = () => {
    setRejectionReason('')
    setShowApproveConfirmModal(false)
    setShowRejectConfirmModal(false)
    setShowReopenConfirmModal(false)
    onClose()
  }

  const isPending = request.status === FranchisorRequestStatus.PENDING
  const isRejected = request.status === FranchisorRequestStatus.REJECTED

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
  const franchiseLogoSrc = request.franchise?.logoUrl
    ? request.franchise.logoUrl.startsWith('http')
      ? request.franchise.logoUrl
      : `${apiUrl}${request.franchise.logoUrl}`
    : null

  return (
    <>
      <BaseModal
        isOpen={isOpen}
        onClose={handleClose}
        tittleText="Solicitação de Franqueador"
        subtittleText="Revise os dados e decida se aprova ou rejeita."
      >
        <div className="space-y-6">
          {/* Badges + data */}
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${modeColors[request.mode]}`}
              >
                {modeLabels[request.mode]}
              </span>
              <span
                className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${statusColors[request.status]}`}
              >
                {statusLabels[request.status]}
              </span>
            </div>
            <div className="text-right text-xs text-gray-500">
              <div>Criado em</div>
              <div className="font-medium text-gray-700">
                {formatDate(request.createdAt)}
              </div>
            </div>
          </div>

          {/* Dados do usuário solicitante */}
          <div className="border border-gray-200 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Usuário solicitante
            </h3>
            {request.user ? (
              <>
                <div className="text-sm text-gray-900 font-medium">
                  {request.user.name}
                </div>
                <div className="text-sm text-gray-600">
                  {request.user.email}
                </div>
              </>
            ) : (
              <div className="text-sm text-gray-500">
                Informações do usuário indisponíveis
              </div>
            )}
          </div>

          {/* Marca — NEW */}
          {request.mode === 'NEW' && (
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">
                Nova marca a ser cadastrada
              </h3>
              <div className="text-base font-medium text-gray-900">
                {request.streamName}
              </div>
              {request.franchise && (
                <div className="text-xs text-gray-500 mt-2">
                  Franquia pré-criada em status {request.franchise.status}{' '}
                  (slug: <code>/{request.franchise.slug ?? '—'}</code>)
                </div>
              )}
              <p className="text-xs text-gray-500 mt-2">
                Ao aprovar, a franquia associada será publicada e o usuário
                receberá permissões de franqueador.
              </p>
            </div>
          )}

          {/* Marca — EXISTING (reivindicação) */}
          {request.mode === 'EXISTING' && (
            <div className="border border-gray-200 rounded-lg p-4 space-y-3">
              <h3 className="text-sm font-semibold text-gray-700">
                Reivindicação de marca existente
              </h3>
              {request.franchise ? (
                <div className="flex items-start gap-3">
                  <div className="w-12 h-12 bg-white rounded border border-gray-200 flex items-center justify-center shrink-0 p-2">
                    {franchiseLogoSrc ? (
                      <Image
                        src={franchiseLogoSrc}
                        alt={request.franchise.name}
                        width={48}
                        height={48}
                        className="object-contain w-full h-full"
                        unoptimized
                      />
                    ) : (
                      <span className="text-2xl" aria-hidden="true">
                        🏢
                      </span>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-base font-medium text-gray-900 truncate">
                      {request.franchise.name}
                    </div>
                    <div className="text-xs text-gray-500">
                      /{request.franchise.slug ?? '—'}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-500">
                  Franquia vinculada não encontrada
                </div>
              )}
              {request.claimReason && (
                <div>
                  <div className="text-xs font-medium text-gray-700 mb-1">
                    Justificativa do solicitante
                  </div>
                  <p className="text-sm text-gray-900 bg-gray-50 rounded p-3 whitespace-pre-wrap">
                    {request.claimReason}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Rejection reason (se já rejeitado) */}
          {isRejected && request.rejectionReason && (
            <div className="border border-red-200 bg-red-50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-red-800 mb-1">
                Motivo da rejeição
              </h3>
              <p className="text-sm text-red-900 whitespace-pre-wrap">
                {request.rejectionReason}
              </p>
              {request.reviewedAt && (
                <div className="text-xs text-red-700 mt-2">
                  Rejeitada em {formatDate(request.reviewedAt)}
                </div>
              )}
            </div>
          )}

          {/* Ações — só pra PENDING */}
          {isPending && (
            <div className="space-y-3 border-t border-gray-200 pt-4">
              <div>
                <label
                  htmlFor="rejectionReason"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Motivo da rejeição (obrigatório se rejeitar)
                </label>
                <textarea
                  id="rejectionReason"
                  rows={3}
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none text-sm"
                  placeholder="Mínimo 10 caracteres. Será enviado ao solicitante por email."
                />
              </div>

              <div className="flex gap-3 justify-end flex-wrap">
                <RoundedButton
                  text="Rejeitar"
                  loadingText="Rejeitando..."
                  loading={rejectMutation.isPending}
                  onClick={handleReject}
                  disabled={rejectMutation.isPending}
                  color="#FFFFFF"
                  hoverColor="#fee2e2"
                  textColor="#dc2626"
                  hoverTextColor="#dc2626"
                  borderColor="#dc2626"
                  type="button"
                />
                <RoundedButton
                  text="Aprovar"
                  loadingText="Aprovando..."
                  loading={approveMutation.isPending}
                  onClick={handleApprove}
                  disabled={approveMutation.isPending}
                  color="#E25E3E"
                  hoverColor="#c04e2e"
                  textColor="#FFFFFF"
                  hoverTextColor="#FFFFFF"
                  type="button"
                />
              </div>
            </div>
          )}

          {/* Reabrir (só REJECTED) */}
          {isRejected && (
            <div className="border-t border-gray-200 pt-4 flex justify-end">
              <RoundedButton
                text="Reabrir solicitação"
                loadingText="Reabrindo..."
                loading={reopenMutation.isPending}
                onClick={handleReopen}
                disabled={reopenMutation.isPending}
                color="#FFFFFF"
                hoverColor="#f3f4f6"
                textColor="#374151"
                hoverTextColor="#111827"
                borderColor="#d1d5db"
                type="button"
              />
            </div>
          )}
        </div>
      </BaseModal>

      <ModalConfirmation
        isOpen={showApproveConfirmModal}
        onClose={() => setShowApproveConfirmModal(false)}
        onConfirm={confirmApprove}
        action="aprovar a solicitação"
        text={`Ao confirmar, ${request.user?.name ?? 'o usuário'} se tornará franqueador${
          request.mode === 'NEW'
            ? ` e a marca "${request.streamName}" será publicada.`
            : request.mode === 'EXISTING' && request.franchise
              ? ` e passará a gerenciar "${request.franchise.name}".`
              : '.'
        } Esta ação pode ser revertida removendo a role do usuário depois.`}
        buttonText="Confirmar aprovação"
        isLoading={approveMutation.isPending}
      />

      <ModalConfirmation
        isOpen={showRejectConfirmModal}
        onClose={() => setShowRejectConfirmModal(false)}
        onConfirm={confirmReject}
        action="rejeitar a solicitação"
        text="O solicitante receberá um email com o motivo da rejeição. Ele poderá criar uma nova solicitação no futuro."
        buttonText="Confirmar rejeição"
        isLoading={rejectMutation.isPending}
      />

      <ModalConfirmation
        isOpen={showReopenConfirmModal}
        onClose={() => setShowReopenConfirmModal(false)}
        onConfirm={confirmReopen}
        action="reabrir a solicitação"
        text="A solicitação voltará para status PENDENTE e poderá ser aprovada ou rejeitada novamente."
        buttonText="Confirmar reabertura"
        isLoading={reopenMutation.isPending}
      />
    </>
  )
}
