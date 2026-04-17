'use client'

import { franchiseQueries } from '@/src/queries/franchises'
import { formatFranchiseName, formatROIRange } from '@/src/utils/formatters'
import { useQuery } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { useMemo, useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import ClockIcon from '../icons/clockIcon'
import DollarSignIcon from '../icons/dollarSignIcon'
import StarIcon from '../icons/starIcon'
import Marquee from '../ui/Marquee'
import ViewModeToggle from '../ranking/ViewModeToggle'
import SponsoredFranchisesTable from './SponsoredFranchisesTable'

const formatCurrency = (value: number | null | undefined) => {
  if (value === null || value === undefined || isNaN(Number(value))) {
    return 'Consulte'
  }
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Number(value))
}

const FeaturedFranchises = () => {
  const router = useRouter()
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table')

  const { data, isLoading } = useQuery(
    franchiseQueries.paginated({
      page: 1,
      limit: 5, // Fetch 5 sponsored franchises
      isSponsored: true, // Only sponsored franchises
    }),
  )

  const sponsoredFranchises = useMemo(
    () =>
      (data?.data || []).filter((franchise) =>
        (franchise.sponsorPlacements || []).includes('HOME_DESTAQUES'),
      ),
    [data?.data],
  )

  const handleFranchiseClick = (franchiseSlug: string) => {
    router.push(`/ranking/${franchiseSlug}`)
  }
  return (
    <section className="py-8 md:py-12 bg-white">
      <div className="container mx-auto px-4">
        <div className="border-t-2 border-[#111] pt-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-baseline gap-3">
              <h2 className="text-[11px] uppercase tracking-[0.8px] font-medium text-[#111]">
                Destaques
              </h2>
              <span className="text-[11px] text-[#888]">
                Selecionadas pelo painel editorial
              </span>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/ranking"
                className="text-[11px] font-medium text-[#E25E3E] hover:underline"
              >
                Ver mais →
              </Link>
              <ViewModeToggle viewMode={viewMode} onChange={setViewMode} />
            </div>
          </div>
        </div>

        {isLoading ? (
          viewMode === 'table' ? (
            <div className="animate-pulse">
              <div className="h-8 bg-secondary/30 mb-1"></div>
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="h-16 border-b border-border"></div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div
                  key={i}
                  className="bg-card rounded-2xl p-6 border border-border shadow-sm animate-pulse"
                >
                  <div className="flex items-start gap-4 mb-4">
                    <div className="w-16 h-16 bg-gray-200 rounded-xl shrink-0"></div>
                    <div className="flex-1 min-w-0">
                      <div className="mb-2 flex items-center gap-2">
                        <div className="h-5 flex-1 bg-gray-200 rounded"></div>
                        <div className="h-5 w-24 shrink-0 bg-gray-200 rounded-full"></div>
                      </div>
                      <div className="h-4 bg-gray-200 rounded w-2/3"></div>
                    </div>
                  </div>
                  <div className="space-y-3 mb-6">
                    <div className="h-4 bg-gray-200 rounded"></div>
                    <div className="h-4 bg-gray-200 rounded"></div>
                  </div>
                  <div className="flex gap-3">
                    <div className="flex-1 h-9 bg-gray-200 rounded-xl"></div>
                    <div className="flex-1 h-9 bg-gray-200 rounded-xl"></div>
                  </div>
                </div>
              ))}
            </div>
          )
        ) : sponsoredFranchises.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            Nenhuma franquia configurada para Destaques encontrada
          </div>
        ) : viewMode === 'table' ? (
          <SponsoredFranchisesTable
            franchises={sponsoredFranchises}
            onClick={handleFranchiseClick}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {sponsoredFranchises.map((franchise) => (
              <div
                key={franchise.id}
                className="bg-white rounded-[16px] p-6 border border-border shadow-sm transition-all duration-300 hover:scale-[1.02] hover:shadow-lg group"
              >
                {/* Header */}
                <div className="flex items-start gap-4 mb-4">
                  <div className="w-16 h-16 bg-white rounded-[12px] border border-border/50 flex items-center justify-center shrink-0 p-3">
                    {franchise.logoUrl ? (
                      <Image
                        src={franchise.logoUrl}
                        alt={franchise.name}
                        width={64}
                        height={64}
                        className="object-contain w-full h-full"
                      />
                    ) : (
                      <span className="text-3xl">🏢</span>
                    )}
                  </div>
                  <div className="flex-1 min-w-0 overflow-hidden">
                    <div className="mb-1 min-w-0 flex items-center">
                      <Marquee className="min-w-0 flex-1">
                        <span className="inline-flex items-center gap-2 whitespace-nowrap">
                          <span className="text-base font-semibold text-foreground">
                            {formatFranchiseName(franchise.name)}
                          </span>
                        </span>
                      </Marquee>
                    </div>
                    <p className="text-sm text-muted-foreground truncate">
                      {franchise.segment || 'N/A'}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 bg-yellow-50 px-2 py-1 rounded-lg shrink-0">
                    <StarIcon
                      width={20}
                      height={20}
                      color="#facc15"
                      filled={true}
                    />
                    <span className="font-semibold text-foreground text-sm">
                      {franchise.averageRating?.toFixed(1) || 'N/A'}
                    </span>
                  </div>
                </div>

                {/* Stats */}
                <div className="space-y-3 mb-6">
                  <div className="flex items-center gap-3 text-sm">
                    <DollarSignIcon
                      width={20}
                      height={20}
                      color="hsl(10 79% 57%)"
                    />
                    <span className="text-muted-foreground">Investimento:</span>
                    <span className="font-medium text-foreground ml-auto">
                      {formatCurrency(franchise.minimumInvestment)}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <ClockIcon width={20} height={20} color="hsl(10 79% 57%)" />
                    <span className="text-muted-foreground">Retorno:</span>
                    <span className="font-medium text-foreground ml-auto">
                      {formatROIRange(
                        franchise.minimumReturnOnInvestment,
                        franchise.maximumReturnOnInvestment,
                      )}
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-3">
                  <Link
                    href={`/ranking/${franchise.slug}`}
                    className="flex-1 rounded-xl border border-border py-2 text-sm font-medium hover:bg-secondary transition-colors text-center"
                  >
                    Ver Detalhes
                  </Link>
                  {(() => {
                    const rawWebsite = franchise.contact?.website?.trim()
                    const websiteUrl =
                      rawWebsite &&
                      (rawWebsite.startsWith('http://') ||
                      rawWebsite.startsWith('https://')
                        ? rawWebsite
                        : `https://${rawWebsite}`)

                    const href = websiteUrl || `/ranking/${franchise.slug}`
                    const isExternal = Boolean(websiteUrl)

                    return (
                      <Link
                        href={href}
                        target={isExternal ? '_blank' : undefined}
                        rel={isExternal ? 'noopener noreferrer' : undefined}
                        className="flex-1 bg-primary hover:bg-coral-dark text-primary-foreground rounded-xl py-2 text-sm font-medium transition-colors text-center"
                      >
                        Contatar
                      </Link>
                    )
                  })()}
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="flex justify-center mt-8">
          <Link
            href="/ranking"
            className="rounded-full border-2 border-border px-5 py-3 md:px-8 md:py-4 text-base md:text-lg font-medium text-[#171726] hover:border-[#E25F3E] hover:text-[#E25F3E] transition-colors"
          >
            Ver Ranking Completo
          </Link>
        </div>
      </div>
    </section>
  )
}

export default FeaturedFranchises
