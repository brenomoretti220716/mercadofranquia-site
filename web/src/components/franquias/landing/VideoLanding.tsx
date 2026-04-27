'use client'

import { useState } from 'react'
import styles from './landing.module.css'

interface VideoLandingProps {
  videoUrls?: string[] | null
}

function youtubeIdFromUrl(url: string): string | null {
  try {
    const u = new URL(url)
    if (u.hostname === 'youtu.be') return u.pathname.slice(1) || null
    if (u.hostname.includes('youtube.com')) {
      const v = u.searchParams.get('v')
      if (v) return v
      const parts = u.pathname.split('/').filter(Boolean)
      if (parts[0] === 'embed' && parts[1]) return parts[1]
    }
    return null
  } catch {
    return null
  }
}

/**
 * Bloco "Conheca a marca" do v10. Layout editorial:
 *   kicker "Vídeo institucional" -> h2 "Conheça a marca" (palavra
 *   'marca' italic accent) -> .video container 16/9 max-width 900px
 *   ink-900 bg + border ink-500.
 *
 * Click-to-play: estado inicial mostra o play button 72px laranja
 * accent-600 sobre fundo dark. Click carrega o iframe (YouTube com
 * autoplay+mute pra contornar a politica de autoplay dos browsers)
 * ou <video> tag (assets diretos). Evita carregar o iframe pesado
 * antes do usuario querer ver, e mantem a estetica editorial em
 * vez do branding do YouTube.
 *
 * Some o bloco inteiro quando nao ha videoUrl valida.
 */
export default function VideoLanding({ videoUrls }: VideoLandingProps) {
  const [playing, setPlaying] = useState(false)
  const url = (videoUrls ?? []).find((u) => u && u.trim())
  if (!url) return null
  const ytId = youtubeIdFromUrl(url)

  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        Conheça a <span className={styles.accent}>marca</span>
      </h2>
      <div className={styles.video}>
        {playing ? (
          ytId ? (
            <iframe
              src={`https://www.youtube.com/embed/${ytId}?autoplay=1&mute=1`}
              title="Vídeo institucional"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          ) : (
            <video src={url} controls autoPlay muted preload="metadata" />
          )
        ) : (
          <button
            type="button"
            aria-label="Reproduzir vídeo institucional"
            className={styles.play}
            onClick={() => setPlaying(true)}
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 16 16"
              style={{ marginLeft: 3 }}
              aria-hidden="true"
            >
              <path d="M3 2L13 8L3 14V2Z" fill="var(--paper)" />
            </svg>
          </button>
        )}
      </div>
    </section>
  )
}
