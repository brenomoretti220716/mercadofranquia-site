'use client'

import { useState } from 'react'
import styles from './landing.module.css'

interface GaleriaLandingProps {
  urls?: string[] | null
}

const VISIBLE = 5

/**
 * Bloco "Veja as lojas" do v10 — hero foto grande no topo + thumbs row
 * horizontal embaixo. Estilo Airbnb sem lightbox.
 *
 * Interacao:
 *   - Clicar em qualquer thumb troca a foto do hero (e a thumb fica
 *     ativa, com outline accent-600).
 *   - Clicar no hero nao faz nada (sem lightbox).
 *   - Clicar na thumb com badge "+N" tambem so vira ativa (mostra a 5a
 *     foto, badge some porque o thumb ficou active).
 *
 * Render:
 *   - 5 thumbs visiveis no desktop, 4 em mobile (5a thumb hidden via
 *     media query :nth-child(5)).
 *   - Se total > 5: primeiras 4 thumbs normais + 5a com badge "+N"
 *     overlay (N = total - 4).
 *   - Se total <= 5: todas thumbs sem badge.
 *
 * Some o bloco inteiro quando urls null/empty.
 */
export default function GaleriaLanding({ urls }: GaleriaLandingProps) {
  const [currentIdx, setCurrentIdx] = useState(0)

  if (!urls || urls.length === 0) return null

  const total = urls.length
  const showOverflow = total > VISIBLE
  const overflowCount = total - (VISIBLE - 1)

  // Thumbs renderizadas: se overflow, primeiras 5 (4 normais + 5a com
  // badge); se nao, todas.
  const thumbsToRender = showOverflow ? urls.slice(0, VISIBLE) : urls

  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        <span className={styles.accent}>Veja</span> as lojas
      </h2>

      <div className={styles.galleryHero}>
        <img
          src={urls[currentIdx]}
          alt={`Foto ${currentIdx + 1}`}
          className={styles.galleryHeroImg}
        />
        <div className={styles.galleryHeroCounter}>
          {String(currentIdx + 1).padStart(2, '0')} /{' '}
          {String(total).padStart(2, '0')}
        </div>
      </div>

      <div className={styles.galleryThumbs}>
        {thumbsToRender.map((url, idx) => {
          const isActive = idx === currentIdx
          const isLastWithOverflow =
            idx === VISIBLE - 1 && showOverflow && !isActive
          return (
            <button
              key={idx}
              type="button"
              aria-label={`Ver foto ${idx + 1}`}
              className={
                isActive
                  ? `${styles.galleryThumb} ${styles.galleryThumbActive}`
                  : styles.galleryThumb
              }
              onClick={() => setCurrentIdx(idx)}
            >
              <img src={url} alt="" className={styles.galleryThumbImg} />
              {isLastWithOverflow && (
                <div className={styles.galleryThumbOverflow}>
                  <span>+{overflowCount}</span>
                </div>
              )}
            </button>
          )
        })}
      </div>
    </section>
  )
}
