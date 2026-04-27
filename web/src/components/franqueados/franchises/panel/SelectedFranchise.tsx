'use client'

import dynamic from 'next/dynamic'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { useRef } from 'react'

import {
  sortDirectionToApi,
  useRankingFilters,
} from '@/src/contexts/RankingContext'
import { useFranchiseRanking } from '@/src/hooks/franchises/useRanking'

import { CommentSectionSkeleton } from '@/src/components/ui/skeletons/CommentSectionSkeleton'
import BannerLanding from '@/src/components/franquias/landing/BannerLanding'
import HeroLanding from '@/src/components/franquias/landing/HeroLanding'
import SelosStripLanding from '@/src/components/franquias/landing/SelosStripLanding'
import ModelosLanding from '@/src/components/franquias/landing/ModelosLanding'
import SobreLanding from '@/src/components/franquias/landing/SobreLanding'
import VideoLanding from '@/src/components/franquias/landing/VideoLanding'
import ProcessStepperLanding from '@/src/components/franquias/landing/ProcessStepperLanding'
import DifferentialsLanding from '@/src/components/franquias/landing/DifferentialsLanding'
import IdealProfileLanding from '@/src/components/franquias/landing/IdealProfileLanding'
import GaleriaLanding from '@/src/components/franquias/landing/GaleriaLanding'
import LeadFormLanding from '@/src/components/franquias/landing/LeadFormLanding'
import ContactFooterLanding from '@/src/components/franquias/landing/ContactFooterLanding'
import landingStyles from '@/src/components/franquias/landing/landing.module.css'
import { normalizeGalleryUrls } from '@/src/utils/franchiseImageUtils'

interface SelectedFranchiseProps {
  selectedFranchise?: string
}

const loadCommentPanel = () =>
  import('@/src/components/franqueados/franchises/comments/CommentPanel')

const CommentPanel = dynamic(loadCommentPanel, {
  loading: () => <CommentSectionSkeleton />,
})

/**
 * Pagina publica da franquia (rota /ranking/[franquia]).
 *
 * Layout v9 — 12 blocos verticalizados em coluna max 720px com bordas
 * line. Cada bloco renderiza condicionalmente: ausente o dado, o
 * bloco some (excecao: Banner, que mostra placeholder hachurado
 * quando bannerUrl null).
 *
 * Ordem v9 (docs/mockups/pagina_publica_franquia_v9.html):
 *   1. Banner full-width
 *   2. Hero (logo + segmento + nome + tagline + 3 metricas + CTA)
 *   3. Strip de selos (placeholder ate fatia futura)
 *   4. Modelos (adaptativo: 0 → fallback investimento; 1+ → cards)
 *   5. Sobre a marca (description + metas de ano)
 *   6. Conheca a marca (video)
 *   7. Como funciona (processSteps)
 *   8. Diferenciais (differentials)
 *   9. Perfil ideal (idealFranchiseeProfile)
 *  10. Veja as lojas (galleryUrls)
 *  11. Reputacao (CommentPanel legado — placeholder ate redesign)
 *  12. Quero saber mais (LeadFormLanding em secao dark)
 *  13. Canais de contato (ContactFooterLanding — extra v9)
 */
export default function SelectedFranchise({
  selectedFranchise,
}: SelectedFranchiseProps) {
  const params = useParams()
  const searchParams = useSearchParams()
  const router = useRouter()
  const franchiseSlug = (params?.franquia as string) || selectedFranchise || ''
  const searchTerm = searchParams.get('search') || ''

  const leadSectionRef = useRef<HTMLDivElement>(null)
  const processStepperRef = useRef<HTMLDivElement>(null)

  const {
    isByDesc,
    isByRatingAverage,
    isByUnits,
    isByInvestment,
    isByReturn,
    isByFranchiseFee,
    isByaverageMonthlyRevenue,
    valueFilters,
  } = useRankingFilters()

  const { franchise } = useFranchiseRanking({
    slug: franchiseSlug,
    search: searchTerm,
    nameSort: sortDirectionToApi(isByDesc),
    ratingSort: sortDirectionToApi(isByRatingAverage),
    unitsSort: sortDirectionToApi(isByUnits),
    investmentSort: sortDirectionToApi(isByInvestment),
    roiSort: sortDirectionToApi(isByReturn),
    franchiseFeeSort: sortDirectionToApi(isByFranchiseFee),
    revenueSort: sortDirectionToApi(isByaverageMonthlyRevenue),
    minInvestment: valueFilters.minInvestment,
    maxInvestment: valueFilters.maxInvestment,
    minROI: valueFilters.minROI,
    maxROI: valueFilters.maxROI,
    minFranchiseFee: valueFilters.minFranchiseFee,
    maxFranchiseFee: valueFilters.maxFranchiseFee,
    minRevenue: valueFilters.minRevenue,
    maxRevenue: valueFilters.maxRevenue,
    minUnits: valueFilters.minUnits,
    maxUnits: valueFilters.maxUnits,
    rating: valueFilters.rating,
    segment: valueFilters.segment,
  })

  const handleBackToRanking = () => router.push('/ranking')

  if (!franchise) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] m-10">
        <h2 className="text-foreground text-xl font-bold mb-2 text-center">
          Esta franquia não está disponível no momento.
        </h2>
        <p className="text-muted-foreground text-base mb-6 text-center max-w-xl">
          Ela pode ter sido desativada ou removida da plataforma.
        </p>
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            Voltar para a página anterior
          </button>
          <button
            onClick={handleBackToRanking}
            className="px-4 py-2 border border-border text-foreground rounded-lg hover:bg-muted transition-colors"
          >
            Ir para o ranking
          </button>
        </div>
      </div>
    )
  }

  const scrollToLead = () => {
    leadSectionRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    })
  }

  const scrollToStepper = () => {
    processStepperRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    })
  }

  return (
    <div className={`${landingStyles.landing} ${landingStyles.page}`}>
      {/* 1. Banner full-width */}
      <BannerLanding
        url={franchise.bannerUrl}
        alt={`Banner ${franchise.name}`}
      />

      {/* 2. Hero */}
      <HeroLanding
        name={franchise.name}
        segment={franchise.segment}
        tagline={franchise.tagline}
        franchiseStartYear={franchise.franchiseStartYear}
        headquarter={franchise.headquarter}
        headquarterState={franchise.headquarterState}
        totalUnits={franchise.totalUnits}
        minimumInvestment={franchise.minimumInvestment}
        maximumInvestment={franchise.maximumInvestment}
        minimumReturnOnInvestment={franchise.minimumReturnOnInvestment}
        maximumReturnOnInvestment={franchise.maximumReturnOnInvestment}
        onCtaClick={scrollToLead}
        onGhostClick={scrollToStepper}
      />

      {/* 3. Strip de selos (placeholder) */}
      <SelosStripLanding selos={null} />

      {/* 4. Modelos disponiveis (adaptativo) */}
      <ModelosLanding
        models={franchise.businessModels}
        franchiseFallback={{
          minimumInvestment: franchise.minimumInvestment,
          maximumInvestment: franchise.maximumInvestment,
          franchiseFee: franchise.franchiseFee,
          minimumReturnOnInvestment: franchise.minimumReturnOnInvestment,
          maximumReturnOnInvestment: franchise.maximumReturnOnInvestment,
        }}
      />

      {/* 5. Sobre a marca (description + metas) */}
      <SobreLanding
        description={franchise.description}
        brandFoundationYear={franchise.brandFoundationYear}
        franchiseStartYear={franchise.franchiseStartYear}
        abfSince={franchise.abfSince}
      />

      {/* 6. Conheca a marca (video) */}
      <VideoLanding videoUrls={normalizeGalleryUrls(franchise.videoUrls)} />

      {/* 7. Como funciona — target do CTA ghost do Hero */}
      <div ref={processStepperRef}>
        <ProcessStepperLanding steps={franchise.processSteps} />
      </div>

      {/* 8. Diferenciais */}
      <DifferentialsLanding items={franchise.differentials} />

      {/* 9. Perfil ideal */}
      <IdealProfileLanding text={franchise.idealFranchiseeProfile} />

      {/* 10. Galeria */}
      <GaleriaLanding urls={normalizeGalleryUrls(franchise.galleryUrls)} />

      {/* 11. Reputacao — bloco legado de Reviews encapsulado em <section> v9 */}
      {franchiseSlug && (
        <section
          className={`${landingStyles.landing} ${landingStyles.section}`}
        >
          <h2 className={landingStyles.heading}>
            <span className={landingStyles.accent}>Reputação</span>
          </h2>
          <CommentPanel
            franchiseId={franchiseSlug}
            isReview={franchise.isReview}
          />
        </section>
      )}

      {/* 12. Quero saber mais — secao dark, target do CTA do Hero */}
      <div ref={leadSectionRef}>
        <LeadFormLanding franchiseName={franchise.name} />
      </div>

      {/* 13. Canais de contato (extra v9, integra a sidecard antiga) */}
      <ContactFooterLanding
        phone={franchise.contact?.phone}
        email={franchise.contact?.email}
        website={franchise.contact?.website}
      />
    </div>
  )
}
