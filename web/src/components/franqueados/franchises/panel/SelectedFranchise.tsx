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
import ReputacaoLanding from '@/src/components/franquias/landing/ReputacaoLanding'
import landingStyles from '@/src/components/franquias/landing/landing.module.css'
import { normalizeGalleryUrls } from '@/src/utils/franchiseImageUtils'

interface SelectedFranchiseProps {
  selectedFranchise?: string
}

/**
 * Pagina publica da franquia (rota /ranking/[franquia]).
 *
 * Layout v9 hibrido (Fatia 1.6) — container .page max 1280px com
 * bordas line, dentro de um .canvas cinza-bege que ocupa o resto do
 * viewport. Conteudo narrativo (Sobre, Como funciona, Diferenciais,
 * Perfil ideal) constrained a 720px centralizado dentro dos blocos
 * full-width pra manter legibilidade.
 *
 * 13 blocos, ordem fixa, condicionais. Excecao: Banner, que mostra
 * placeholder hachurado quando bannerUrl null (nao some).
 *
 * Ordem v9 (docs/mockups/pagina_publica_franquia_v9.html):
 *   1. Banner full-width (BannerLanding)
 *   2. Hero (HeroLanding) — logo + segmento + nome + tagline +
 *      metricas + CTA scroll
 *   3. Strip de selos (SelosStripLanding placeholder)
 *   4. Modelos (ModelosLanding adaptativo)
 *   5. Sobre a marca (SobreLanding com description + metas anos)
 *   6. Conheca a marca (VideoLanding embed YT/nativo)
 *   7. Como funciona (ProcessStepperLanding)
 *   8. Diferenciais (DifferentialsLanding)
 *   9. Perfil ideal (IdealProfileLanding)
 *  10. Veja as lojas (GaleriaLanding 4/3/2 cols responsivo)
 *  11. Reputacao (ReputacaoLanding — Fatia 1.6 redesign nativo v9
 *      com filtros client-side, lista 2 cols, empty state)
 *  12. Quero saber mais (LeadFormLanding secao dark, target do CTA)
 *  13. Canais de contato (ContactFooterLanding)
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
    <div className={`${landingStyles.landing} ${landingStyles.canvas}`}>
      <div className={landingStyles.page}>
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
          minimumInvestment={franchise.minimumInvestment}
          maximumInvestment={franchise.maximumInvestment}
          minimumReturnOnInvestment={franchise.minimumReturnOnInvestment}
          maximumReturnOnInvestment={franchise.maximumReturnOnInvestment}
          totalUnits={franchise.totalUnits}
          onCtaClick={scrollToLead}
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

        {/* 7. Como funciona */}
        <ProcessStepperLanding steps={franchise.processSteps} />

        {/* 8. Diferenciais */}
        <DifferentialsLanding items={franchise.differentials} />

        {/* 9. Perfil ideal */}
        <IdealProfileLanding text={franchise.idealFranchiseeProfile} />

        {/* 10. Galeria */}
        <GaleriaLanding urls={normalizeGalleryUrls(franchise.galleryUrls)} />

        {/* 11. Reputacao — Fatia 1.6 substitui CommentPanel pelo
          ReputacaoLanding (design v9 nativo, filtros client-side, empty
          state). */}
        {franchiseSlug && (
          <ReputacaoLanding
            franchiseId={franchiseSlug}
            averageRating={franchise.averageRating}
            reviewCount={franchise.reviewCount}
          />
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
    </div>
  )
}
