'use client'

import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { useRef } from 'react'

import {
  sortDirectionToApi,
  useRankingFilters,
} from '@/src/contexts/RankingContext'
import { useFranchiseRanking } from '@/src/hooks/franchises/useRanking'

import BannerLanding from '@/src/components/franquias/landing/BannerLanding'
import HeroLanding from '@/src/components/franquias/landing/HeroLanding'
import ModelosLanding from '@/src/components/franquias/landing/ModelosLanding'
import SobreLanding from '@/src/components/franquias/landing/SobreLanding'
import VideoLanding from '@/src/components/franquias/landing/VideoLanding'
import ProcessStepperLanding from '@/src/components/franquias/landing/ProcessStepperLanding'
import DifferentialsLanding from '@/src/components/franquias/landing/DifferentialsLanding'
import IdealProfileLanding from '@/src/components/franquias/landing/IdealProfileLanding'
import GaleriaLanding from '@/src/components/franquias/landing/GaleriaLanding'
import ReputacaoLanding from '@/src/components/franquias/landing/ReputacaoLanding'
import LeadFormLanding from '@/src/components/franquias/landing/LeadFormLanding'
import landingStyles from '@/src/components/franquias/landing/landing.module.css'
import { normalizeGalleryUrls } from '@/src/utils/franchiseImageUtils'

interface SelectedFranchiseProps {
  selectedFranchise?: string
}

/**
 * Pagina publica da franquia (rota /ranking/[franquia]).
 *
 * Layout v9 — 12 blocos verticalizados em coluna max 720px com bordas
 * line. Cada bloco renderiza condicionalmente: ausente o dado, o
 * bloco some (excecao: Banner, que mostra placeholder hachurado
 * quando bannerUrl null).
 *
 * Ordem v10 (docs/mockups/pagina_publica_franquia_v10_handoff.html),
 * funil de decisao do investidor:
 *   1. Banner full-width
 *   2. Hero (logo+nome row + meta inline + KPI strip + CTA primario)
 *   3. Modelos (adaptativo: ficha tecnica se 0 modelos; cards bege
 *      com 5 metricas-chave per-modelo se >=1)
 *   4. Diferenciais (numerados)
 *   5. Sobre a marca (description em text-block 16px)
 *   6. Vídeo (16/9 com YouTube embed direto ou play link)
 *   7. Perfil ideal (text-block)
 *   8. Como funciona (stepper Instrument Serif italic 64px)
 *   9. Galeria (grid responsivo)
 *  10. Reputacao (stat + filtro star bar + 5 reviews + link pra
 *      pagina dedicada — Fatia 1.10)
 *  11. Quero saber mais (LeadFormLanding em secao dark, 2 colunas)
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
        logoUrl={franchise.logoUrl}
        franchiseStartYear={franchise.franchiseStartYear}
        headquarter={franchise.headquarter}
        headquarterState={franchise.headquarterState}
        totalUnits={franchise.totalUnits}
        minimumInvestment={franchise.minimumInvestment}
        maximumInvestment={franchise.maximumInvestment}
        minimumReturnOnInvestment={franchise.minimumReturnOnInvestment}
        maximumReturnOnInvestment={franchise.maximumReturnOnInvestment}
        onCtaClick={scrollToLead}
      />

      {/* 3. Modelos disponiveis (adaptativo: ficha tecnica enxuta com 5
          linhas se 0 modelos; cards bege per-modelo se >=1) */}
      <ModelosLanding
        models={franchise.businessModels}
        minimumInvestment={franchise.minimumInvestment}
        maximumInvestment={franchise.maximumInvestment}
        minimumReturnOnInvestment={franchise.minimumReturnOnInvestment}
        maximumReturnOnInvestment={franchise.maximumReturnOnInvestment}
        averageMonthlyRevenue={franchise.averageMonthlyRevenue}
        workingCapital={franchise.workingCapital}
        storeArea={franchise.storeArea}
      />

      {/*
        Ordem dos blocos a partir daqui segue o funil de decisao do
        investidor (definido na Fatia 1.8):
          4. Diferenciais     — responde "porque vale o preco?" logo
                                apos os Modelos, antes do contexto.
          5. Sobre a marca    — contexto editorial antes da experiencia
                                emocional.
          6. Vídeo            — experiencia emocional / demo da marca.
          7. Perfil ideal     — "eu sirvo?" antes de "como entro?".
          8. Como funciona    — processo de entrada.
          9. Galeria          — confirmacao visual depois do processo,
                                antes da reputacao.
      */}

      {/* 4. Diferenciais */}
      <DifferentialsLanding items={franchise.differentials} />

      {/* 5. Sobre a marca (description) — metas de ano vivem no heroMeta */}
      <SobreLanding description={franchise.description} />

      {/* 6. Conheca a marca (video) */}
      <VideoLanding videoUrls={normalizeGalleryUrls(franchise.videoUrls)} />

      {/* 7. Perfil ideal */}
      <IdealProfileLanding text={franchise.idealFranchiseeProfile} />

      {/* 8. Como funciona */}
      <ProcessStepperLanding steps={franchise.processSteps} />

      {/* 9. Galeria */}
      <GaleriaLanding urls={normalizeGalleryUrls(franchise.galleryUrls)} />

      {/* 10. Reputacao — stat + filtro star bar + 5 reviews + link pra
          pagina dedicada (Fatia 1.10 backlog). */}
      <ReputacaoLanding
        reviews={franchise.reviews}
        averageRating={franchise.averageRating}
        reviewCount={franchise.reviewCount}
        franchiseSlug={franchiseSlug}
      />

      {/* 11. Quero saber mais — secao dark, target do CTA do Hero */}
      <div ref={leadSectionRef}>
        <LeadFormLanding
          franchiseName={franchise.name}
          franchiseSegment={franchise.segment}
        />
      </div>
    </div>
  )
}
