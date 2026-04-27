'use client'

import { useState } from 'react'
import Link from 'next/link'
import type { Review } from '@/src/schemas/franchises/Reviews'
import styles from './landing.module.css'

interface ReputacaoLandingProps {
  reviews?: Review[] | null
  averageRating?: number | null
  reviewCount?: number | null
  franchiseSlug: string
}

type StarFilter = 'all' | 1 | 2 | 3 | 4 | 5

const VISIBLE_LIMIT = 5

function renderStars(rating: number): string {
  const filled = Math.max(0, Math.min(5, Math.round(rating)))
  return '★'.repeat(filled) + '☆'.repeat(5 - filled)
}

function formatDate(value: string | Date): string {
  const d = typeof value === 'string' ? new Date(value) : value
  return new Intl.DateTimeFormat('pt-BR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(d)
}

function formatRelativeDate(value: string | Date): string {
  const d = typeof value === 'string' ? new Date(value) : value
  const now = Date.now()
  const diffMs = d.getTime() - now
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24))
  const rtf = new Intl.RelativeTimeFormat('pt-BR', { numeric: 'auto' })
  if (Math.abs(diffDays) < 30) return rtf.format(diffDays, 'day')
  const diffMonths = Math.round(diffDays / 30)
  if (Math.abs(diffMonths) < 12) return rtf.format(diffMonths, 'month')
  const diffYears = Math.round(diffDays / 365)
  return rtf.format(diffYears, 'year')
}

/**
 * Bloco "Reputacao" da landing publica v10. Editorial — drop do
 * CommentPanel legacy.
 *
 * Estrutura:
 *   h2 "Reputação" italic accent
 *   repStat — avg 64px Instrument Serif + estrelas accent + meta
 *     ("N avaliacoes · X% recomendam")
 *   starbar — 6 celulas (Todas + 5/4/3/2/1) com count por rating
 *     active vira inverted dark; disabled fica opacity 0.3
 *   repList — 5 reviews (slice). Cada review:
 *     header (estrelas + nome + badge anonimo + data)
 *     comment 15px ink-900
 *     response opcional (paper-warm bg + accent-600 border-left)
 *   repActions — counter "Mostrando A de B" + link "Ver todas" (se
 *     totalCount > 5) + button "+ Avaliar" (placeholder, abre modal
 *     em fatia futura)
 *
 * Filtragem star bar local: clica em rating → lista filtra ate 5.
 * Link "Ver todas" carrega o filtro via query string pra rota
 * dedicada /ranking/{slug}/avaliacoes (Fatia 1.10).
 *
 * Some o bloco inteiro quando reviewCount === 0.
 */
export default function ReputacaoLanding({
  reviews,
  averageRating,
  reviewCount,
  franchiseSlug,
}: ReputacaoLandingProps) {
  const [activeFilter, setActiveFilter] = useState<StarFilter>('all')

  const safeReviews = reviews ?? []
  const safeReviewCount = reviewCount ?? safeReviews.length

  // Counts por rating — index 0 nao usado, 1-5 com contagem.
  const countByRating = [0, 0, 0, 0, 0, 0]
  for (const r of safeReviews) {
    if (r.rating >= 1 && r.rating <= 5) countByRating[r.rating]++
  }

  // % recomendam = rating >= 4. null se 0 reviews (skip do sufixo).
  const recommendPct =
    safeReviews.length > 0
      ? Math.round(
          (safeReviews.filter((r) => r.rating >= 4).length /
            safeReviews.length) *
            100,
        )
      : null

  if (safeReviewCount === 0) return null

  const filteredReviews =
    activeFilter === 'all'
      ? safeReviews
      : safeReviews.filter((r) => r.rating === activeFilter)
  const totalCount = filteredReviews.length
  const visibleReviews = filteredReviews.slice(0, VISIBLE_LIMIT)

  const allHrefBase = `/ranking/${franchiseSlug}/avaliacoes`
  const seeAllHref =
    activeFilter === 'all'
      ? allHrefBase
      : `${allHrefBase}?rating=${activeFilter}`

  const avg = averageRating ?? 0

  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        <span className={styles.accent}>Reputação</span>
      </h2>

      <div className={styles.repStat}>
        <div className={styles.repAvg}>{avg.toFixed(1)}</div>
        <div>
          <div className={styles.repStars}>{renderStars(avg)}</div>
          <div className={styles.repMeta}>
            <b>{safeReviewCount}</b> avaliações
            {recommendPct !== null && (
              <>
                {' · '}
                <b>{recommendPct}%</b> recomendam
              </>
            )}
          </div>
        </div>
      </div>

      <div className={styles.starbar} role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeFilter === 'all'}
          className={
            activeFilter === 'all'
              ? `${styles.starbarCell} ${styles.starbarCellActive}`
              : styles.starbarCell
          }
          onClick={() => setActiveFilter('all')}
        >
          <div className={styles.starbarRating}>Todas</div>
          <div className={styles.starbarCount}>{safeReviews.length}</div>
        </button>
        {([5, 4, 3, 2, 1] as const).map((rating) => {
          const count = countByRating[rating]
          const disabled = count === 0
          const active = activeFilter === rating
          const classes = [styles.starbarCell]
          if (active) classes.push(styles.starbarCellActive)
          if (disabled) classes.push(styles.starbarCellDisabled)
          return (
            <button
              key={rating}
              type="button"
              role="tab"
              aria-selected={active}
              disabled={disabled}
              className={classes.join(' ')}
              onClick={() => {
                if (!disabled) setActiveFilter(rating)
              }}
            >
              <div className={styles.starbarRating}>{rating}★</div>
              <div className={styles.starbarCount}>{count}</div>
            </button>
          )
        })}
      </div>

      <div className={styles.repList}>
        {visibleReviews.map((review) => {
          const response = review.responses?.[0] ?? null
          const authorName = review.anonymous
            ? 'Investidor'
            : (review.author?.name ?? 'Investidor')
          return (
            <article key={review.id} className={styles.repItem}>
              <div className={styles.repHeader}>
                <span className={styles.repStarsRow}>
                  {renderStars(review.rating)}
                </span>
                <span className={styles.repAuthor}>{authorName}</span>
                {review.anonymous && (
                  <span className={styles.repBadgeAnon}>Anônimo</span>
                )}
                <span className={styles.repWhen}>
                  {formatDate(review.createdAt)}
                </span>
              </div>
              <p className={styles.repText}>{review.comment}</p>
              {response && (
                <div className={styles.repResponse}>
                  <div className={styles.repResponseLabel}>
                    Resposta da marca · {formatRelativeDate(response.createdAt)}
                  </div>
                  <div className={styles.repResponseText}>
                    {response.content}
                  </div>
                </div>
              )}
            </article>
          )
        })}
      </div>

      <div className={styles.repActions}>
        <div className={styles.repCounter}>
          Mostrando <b>{Math.min(VISIBLE_LIMIT, totalCount)}</b> de{' '}
          <b>{totalCount}</b>
        </div>
        <div className={styles.repCtaGroup}>
          {totalCount > VISIBLE_LIMIT && (
            <Link href={seeAllHref} className={styles.ctaGhost}>
              Ver todas as {totalCount} avaliações →
            </Link>
          )}
          {/* TODO: wire pro modal de criar avaliacao em fatia futura. */}
          <button type="button" className={styles.ctaAdd}>
            + Avaliar
          </button>
        </div>
      </div>
    </section>
  )
}
