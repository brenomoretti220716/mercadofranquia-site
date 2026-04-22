'use client'

import Image from 'next/image'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { ExternalLink, Plus, Rocket } from 'lucide-react'
import { franchiseQueries } from '@/src/queries/franchises'
import { useAuth } from '@/src/hooks/users/useAuth'
import RoundedButton from '@/src/components/ui/RoundedButton'
import FranchiseStatusBanner from './FranchiseStatusBanner'

interface MyFranchisesListProps {
  onCreateNew: () => void
}

/**
 * Lista todas as Franchises do franqueador autenticado (qualquer status).
 * Cada card mostra banner de status + logo + nome + slug + link pro site (se APPROVED).
 * Botão "Nova marca" no topo pra acionar o form de criar marca adicional.
 */
export default function MyFranchisesList({
  onCreateNew,
}: MyFranchisesListProps) {
  const { token, payload } = useAuth()
  const isFranchisor = payload?.role === 'FRANCHISOR'

  const { data, isLoading, isError } = useQuery({
    ...franchiseQueries.myFranchises(token || ''),
    enabled: !!token && isFranchisor,
  })

  // User não-FRANCHISOR (MEMBER): estado de primeiro acesso.
  // Não chama a query (enabled: false), então não mostra loading/error —
  // cai direto no CTA de cadastrar marca.
  if (!isFranchisor) {
    return (
      <div className="m-4 sm:m-6 md:m-10">
        <div className="rounded-2xl border-2 border-dashed border-gray-200 bg-white p-8 md:p-12 text-center">
          <div className="mx-auto w-12 h-12 rounded-full bg-[#FFF4F0] flex items-center justify-center mb-4">
            <Rocket className="w-6 h-6 text-[#E25E3E]" aria-hidden="true" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Cadastre sua franquia no Mercado Franquia
          </h3>
          <p className="text-sm text-gray-600 max-w-md mx-auto mb-6">
            Se você é dono de uma franquia, cadastre sua marca e ganhe
            visibilidade para investidores e futuros franqueados. Nossa equipe
            analisa cada solicitação individualmente.
          </p>
          <RoundedButton
            text="Cadastrar minha franquia"
            onClick={onCreateNew}
            color="#E25E3E"
            hoverColor="#c04e2e"
            textColor="#FFFFFF"
            hoverTextColor="#FFFFFF"
          />
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-muted-foreground text-lg">
          Carregando suas franquias...
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] m-4 sm:m-6 md:m-10 text-center">
        <h2 className="text-xl font-semibold text-foreground mb-2">
          Não conseguimos carregar suas franquias
        </h2>
        <p className="text-muted-foreground text-base max-w-md mb-6">
          Tente recarregar a página. Se o problema persistir, entre em contato
          com nossa equipe.
        </p>
      </div>
    )
  }

  const franchises = data?.data ?? []

  return (
    <div className="m-4 sm:m-6 md:m-10">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-foreground">
            Minhas franquias
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {franchises.length === 0
              ? 'Você ainda não tem marcas cadastradas'
              : franchises.length === 1
                ? '1 marca cadastrada'
                : `${franchises.length} marcas cadastradas`}
          </p>
        </div>
        <button
          type="button"
          onClick={onCreateNew}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-full hover:bg-primary/90 transition-colors text-sm font-medium"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Nova marca
        </button>
      </div>

      {franchises.length === 0 ? (
        <div className="flex flex-col items-center justify-center min-h-[300px] bg-white rounded-2xl border border-border/50 p-8 text-center">
          <p className="text-muted-foreground text-base max-w-md mb-4">
            Cadastre sua primeira marca pra começar a receber leads de
            investidores interessados.
          </p>
          <button
            type="button"
            onClick={onCreateNew}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-full hover:bg-primary/90 transition-colors text-sm font-medium"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            Cadastrar primeira marca
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {franchises.map((franchise) => (
            <FranchiseCard key={franchise.id} franchise={franchise} />
          ))}
        </div>
      )}
    </div>
  )
}

interface FranchiseCardProps {
  franchise: {
    id: string
    name: string
    slug: string | null
    logoUrl?: string | null
    status?: 'PENDING' | 'APPROVED' | 'REJECTED'
    isActive: boolean
  }
}

function FranchiseCard({ franchise }: FranchiseCardProps) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
  const logoSrc = franchise.logoUrl
    ? franchise.logoUrl.startsWith('http')
      ? franchise.logoUrl
      : `${apiUrl}${franchise.logoUrl}`
    : null

  return (
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
          {franchise.slug && (
            <p className="text-xs text-muted-foreground mt-0.5">
              /{franchise.slug}
            </p>
          )}
        </div>

        {franchise.status === 'APPROVED' && franchise.slug && (
          <Link
            href={`/ranking/${franchise.slug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline shrink-0"
          >
            Ver no site
            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        )}
      </div>

      <FranchiseStatusBanner
        status={franchise.status}
        franchiseName={franchise.name}
      />
    </div>
  )
}
