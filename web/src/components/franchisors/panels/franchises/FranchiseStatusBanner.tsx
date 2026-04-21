'use client'

import { CheckCircle2, Clock, XCircle } from 'lucide-react'

interface FranchiseStatusBannerProps {
  status?: 'PENDING' | 'APPROVED' | 'REJECTED' | null
  franchiseName?: string
  rejectionReason?: string | null
  className?: string
}

/**
 * Banner visual que indica o status de aprovação de uma Franchise.
 * - APPROVED (verde): franquia publicada e visível no site
 * - PENDING (amarelo): aguardando revisão admin
 * - REJECTED (vermelho): não aprovada, mostra motivo
 *
 * Se status for null/undefined, não renderiza nada.
 */
export default function FranchiseStatusBanner({
  status,
  franchiseName,
  rejectionReason,
  className = '',
}: FranchiseStatusBannerProps) {
  if (!status) return null

  const configs = {
    APPROVED: {
      icon: CheckCircle2,
      bg: 'bg-green-50',
      border: 'border-green-200',
      iconColor: 'text-green-600',
      titleColor: 'text-green-900',
      bodyColor: 'text-green-800',
      title: 'Marca aprovada',
      body: franchiseName
        ? `${franchiseName} está publicada e visível no site.`
        : 'Sua franquia está publicada e visível no site.',
    },
    PENDING: {
      icon: Clock,
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      iconColor: 'text-amber-600',
      titleColor: 'text-amber-900',
      bodyColor: 'text-amber-800',
      title: 'Em análise pela equipe',
      body: franchiseName
        ? `${franchiseName} está aguardando aprovação. Você será notificado por email.`
        : 'Sua marca está aguardando aprovação da nossa equipe.',
    },
    REJECTED: {
      icon: XCircle,
      bg: 'bg-red-50',
      border: 'border-red-200',
      iconColor: 'text-red-600',
      titleColor: 'text-red-900',
      bodyColor: 'text-red-800',
      title: 'Não aprovada',
      body: rejectionReason
        ? `Motivo: ${rejectionReason}`
        : 'Não foi possível aprovar esta marca. Entre em contato com a equipe.',
    },
  } as const

  const cfg = configs[status]
  const Icon = cfg.icon

  return (
    <div
      className={`flex items-start gap-3 rounded-xl border p-4 ${cfg.bg} ${cfg.border} ${className}`}
      role="status"
      aria-live="polite"
    >
      <Icon
        className={`h-5 w-5 shrink-0 mt-0.5 ${cfg.iconColor}`}
        aria-hidden="true"
      />
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-semibold ${cfg.titleColor}`}>{cfg.title}</p>
        <p className={`text-sm mt-0.5 ${cfg.bodyColor}`}>{cfg.body}</p>
      </div>
    </div>
  )
}
