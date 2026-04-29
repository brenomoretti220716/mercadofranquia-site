'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import styles from './landing.module.css'

interface GaleriaLandingProps {
  urls?: string[] | null
}

/**
 * Bloco "Veja as lojas" do v10 — hero foto grande no topo + thumbs row
 * horizontal embaixo. Estilo Airbnb sem lightbox.
 *
 * Navegação:
 *   - Setas ←/→ no hero navegam circularmente entre TODAS as fotos
 *   - ArrowLeft/ArrowRight no teclado fazem o mesmo
 *   - Click em qualquer thumb troca foto do hero
 *
 * Render:
 *   - Thumbs num row horizontal com scroll lateral (overflow-x: auto).
 *     5 thumbs cabem na viewport desktop, 4 no mobile — o resto fica
 *     acessível via scroll.
 *   - Quando currentIdx muda, auto-scrolla pra centralizar a thumb
 *     ativa via scrollTo({ behavior: 'smooth' }).
 *
 * Some o bloco inteiro quando urls null/empty.
 */
export default function GaleriaLanding({ urls }: GaleriaLandingProps) {
  const [currentIdx, setCurrentIdx] = useState(0)
  const thumbsContainerRef = useRef<HTMLDivElement>(null)

  const total = urls?.length ?? 0

  const goPrev = useCallback(() => {
    setCurrentIdx((i) => (i - 1 + total) % total)
  }, [total])

  const goNext = useCallback(() => {
    setCurrentIdx((i) => (i + 1) % total)
  }, [total])

  // Suporte a teclado: setas esquerda/direita
  useEffect(() => {
    if (total === 0) return
    const onKey = (e: KeyboardEvent) => {
      // Pula se foco está em input/textarea/contenteditable
      const target = e.target as HTMLElement | null
      if (target) {
        const tag = target.tagName
        if (tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable) {
          return
        }
      }
      if (e.key === 'ArrowLeft') goPrev()
      else if (e.key === 'ArrowRight') goNext()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [goPrev, goNext, total])

  // Auto-scroll do row de thumbs pra centralizar a ativa quando currentIdx muda
  useEffect(() => {
    const container = thumbsContainerRef.current
    if (!container) return
    const activeThumb = container.children[currentIdx] as
      | HTMLElement
      | undefined
    if (!activeThumb) return

    const containerWidth = container.clientWidth
    const thumbLeft = activeThumb.offsetLeft
    const thumbWidth = activeThumb.clientWidth
    const targetScroll = thumbLeft - containerWidth / 2 + thumbWidth / 2

    container.scrollTo({ left: targetScroll, behavior: 'smooth' })
  }, [currentIdx])

  if (!urls || urls.length === 0) return null

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

        {total > 1 && (
          <>
            <button
              type="button"
              aria-label="Foto anterior"
              className={`${styles.galleryHeroNav} ${styles.galleryHeroNavPrev}`}
              onClick={goPrev}
            >
              ←
            </button>
            <button
              type="button"
              aria-label="Próxima foto"
              className={`${styles.galleryHeroNav} ${styles.galleryHeroNavNext}`}
              onClick={goNext}
            >
              →
            </button>
          </>
        )}

        <div className={styles.galleryHeroCounter}>
          {String(currentIdx + 1).padStart(2, '0')} /{' '}
          {String(total).padStart(2, '0')}
        </div>
      </div>

      <div className={styles.galleryThumbs} ref={thumbsContainerRef}>
        {urls.map((url, idx) => {
          const isActive = idx === currentIdx
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
            </button>
          )
        })}
      </div>
    </section>
  )
}
