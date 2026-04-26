'use client'

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'

import { reviewQueries } from '@/src/queries/reviews'
import type { Review } from '@/src/schemas/franchises/Reviews'

import styles from './landing.module.css'

interface ReputacaoLandingProps {
  franchiseId: string
  averageRating?: number | null
  reviewCount?: number | null
}

type StarFilter = 'all' | 1 | 2 | 3 | 4 | 5

function formatRelativeDate(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  const days = Math.floor(ms / (1000 * 60 * 60 * 24))
  if (days < 1) return 'hoje'
  if (days === 1) return 'há 1 dia'
  if (days < 30) return `há ${days} dias`
  const months = Math.floor(days / 30)
  if (months === 1) return 'há 1 mês'
  if (months < 12) return `há ${months} meses`
  const years = Math.floor(months / 12)
  return years === 1 ? 'há 1 ano' : `há ${years} anos`
}

function starsRow(rating: number, full = '★', empty = '☆'): string {
  const r = Math.max(0, Math.min(5, Math.round(rating)))
  return full.repeat(r) + empty.repeat(5 - r)
}

/**
 * Bloco "Reputacao" do v9 — substitui o CommentPanel legado da pagina
 * publica. Layout per docs/mockups/pagina_publica_franquia_v9.html
 * secao 11.
 *
 * Composicao:
 * - h2 "**Reputacao**" (palavra inteira em Fraunces italic laranja)
 * - Stat row: avg rating + 5 estrelas + meta "X avaliacoes · Y%
 *   recomendam" (esconde no empty state)
 * - Filtros por estrela (Todas / 5★ / 4★ / 3★ / 2★ / 1★) com
 *   contadores; client-side, esconde no empty state
 * - Lista 2 cols desktop / 1 col tablet+mobile
 * - Action row: "Ver todas (N)" ghost + "Avaliar essa franquia" ink
 *
 * Empty state (0 reviews ativos): mensagem centralizada + botao
 * "Avaliar". Sem stats, sem filtros.
 *
 * Submit/listing endpoint nao foi tocado. Buscamos via
 * reviewQueries.byFranchisePaginated com limit alto (50) — paginacao
 * UI fica pra fatia futura. % recomendam = reviews com rating >= 4 /
 * total (calculo client-side; nao ha campo no DB).
 *
 * Acoes "Ver todas" e "Avaliar essa franquia": stub com toast — rotas
 * dedicadas entram em fatia futura. Mantido visualmente per v9.
 */
export default function ReputacaoLanding({
  franchiseId,
  averageRating,
  reviewCount,
}: ReputacaoLandingProps) {
  const [filter, setFilter] = useState<StarFilter>('all')

  const { data: reviewsPage } = useQuery({
    ...reviewQueries.byFranchisePaginated(franchiseId, 1, 50),
    enabled: !!franchiseId,
  })

  const allReviews: Review[] = useMemo(
    () => ((reviewsPage?.data as Review[]) || []).filter((r) => r.isActive),
    [reviewsPage],
  )

  const total = reviewCount ?? allReviews.length
  const isEmpty = total === 0

  // Contadores por estrela (1-5) pra labels dos filtros
  const counts = useMemo(() => {
    const c: Record<1 | 2 | 3 | 4 | 5, number> = {
      1: 0,
      2: 0,
      3: 0,
      4: 0,
      5: 0,
    }
    for (const r of allReviews) {
      const k = Math.max(1, Math.min(5, Math.round(r.rating))) as
        | 1
        | 2
        | 3
        | 4
        | 5
      c[k] += 1
    }
    return c
  }, [allReviews])

  const recommendedPct = useMemo(() => {
    if (allReviews.length === 0) return null
    const positive = allReviews.filter((r) => r.rating >= 4).length
    return Math.round((positive / allReviews.length) * 100)
  }, [allReviews])

  const visible = useMemo(() => {
    if (filter === 'all') return allReviews
    return allReviews.filter((r) => Math.round(r.rating) === filter)
  }, [allReviews, filter])

  const stub = (label: string) =>
    toast.info(`${label} entra em fatia futura — rota ainda nao implementada.`)

  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        <span className={styles.accent}>Reputação</span>
      </h2>

      {isEmpty ? (
        <div className={styles.reputationEmpty}>
          <p className={styles.reputationEmptyText}>
            Esta franquia ainda não tem avaliações.
          </p>
          <button
            type="button"
            className={`${styles.btn} ${styles.btnSecondary}`}
            style={{ width: 'auto', minWidth: 220, padding: '12px 24px' }}
            onClick={() => stub('Avaliar essa franquia')}
          >
            Avaliar essa franquia
          </button>
        </div>
      ) : (
        <>
          <div className={styles.reputationStat}>
            <div className={styles.reputationAvg}>
              {(averageRating ?? 0).toFixed(1)}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div className={styles.reputationStarsRow}>
                {starsRow(averageRating ?? 0)}
              </div>
              <div className={styles.reputationMeta}>
                {total} avaliações
                {recommendedPct !== null
                  ? ` · ${recommendedPct}% recomendam`
                  : ''}
              </div>
            </div>
          </div>

          <div className={styles.reviewFilters}>
            <button
              type="button"
              className={`${styles.reviewFilter} ${filter === 'all' ? styles.reviewFilterActive : ''}`}
              onClick={() => setFilter('all')}
            >
              Todas
            </button>
            {([5, 4, 3, 2, 1] as const).map((star) => (
              <button
                key={star}
                type="button"
                className={`${styles.reviewFilter} ${filter === star ? styles.reviewFilterActive : ''}`}
                onClick={() => setFilter(star)}
              >
                {star} ★ ({counts[star]})
              </button>
            ))}
          </div>

          <div className={styles.reviewList}>
            {visible.map((r) => {
              // API returns author as { id, name } (nullable when anonymous);
              // o TS schema legado declara authorName top-level mas o backend
              // serializer (_serialize_review) nao popula esse campo. Preferir
              // r.author?.name e cair pra authorName so como fallback de compat.
              type ReviewWithAuthor = typeof r & {
                author?: { name?: string | null } | null
              }
              const reviewExt = r as ReviewWithAuthor
              const author = r.anonymous
                ? 'Investidor anônimo'
                : (reviewExt.author?.name ?? r.authorName ?? 'Investidor')
              // Response da marca: backend atual NAO retorna r.responses neste
              // endpoint (apenas selectinload de Review.author). Resposta da
              // marca so vai renderizar quando backend incluir o campo (fatia
              // futura). Optional chain mantem comportamento gracefull.
              const response = r.responses && r.responses[0]
              return (
                <div key={r.id} className={styles.reviewItem}>
                  <div className={styles.reviewHeader}>
                    <div className={styles.reviewStars}>
                      {starsRow(r.rating)}
                    </div>
                    <div className={styles.reviewAuthor}>{author}</div>
                    {/* Fatia 1.7 — badge "Franqueado verificado" removida
                        do design. Campo isFranchisee continua no DB e na
                        response, so nao renderiza mais. Badge "Anônimo"
                        permanece (diferenciacao com nome vs sem nome
                        ainda agrega valor ao leitor). */}
                    {r.anonymous && (
                      <div
                        className={`${styles.reviewBadge} ${styles.reviewBadgeAnon}`}
                      >
                        Anônimo
                      </div>
                    )}
                    <div className={styles.reviewWhen}>
                      {formatRelativeDate(r.createdAt)}
                    </div>
                  </div>
                  <p className={styles.reviewText}>{r.comment}</p>
                  {response && (
                    <div className={styles.reviewResponse}>
                      <div className={styles.reviewResponseLabel}>
                        Resposta da marca ·{' '}
                        {formatRelativeDate(String(response.createdAt))}
                      </div>
                      <div className={styles.reviewResponseText}>
                        {response.content}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          <div className={styles.reviewCtaRow}>
            <button
              type="button"
              className={`${styles.btn} ${styles.btnGhost}`}
              onClick={() => stub('Ver todas as avaliações')}
            >
              Ver todas ({total})
            </button>
            <button
              type="button"
              className={`${styles.btn} ${styles.btnSecondary}`}
              onClick={() => stub('Avaliar essa franquia')}
            >
              Avaliar essa franquia
            </button>
          </div>
        </>
      )}
    </section>
  )
}
