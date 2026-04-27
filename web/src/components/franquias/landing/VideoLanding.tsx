import styles from './landing.module.css'

interface VideoLandingProps {
  videoUrls?: string[] | null
}

/**
 * Converte URL do YouTube (varias formas: watch?v=, youtu.be/, embed/)
 * pra URL de embed canonica. Retorna null se nao for YouTube.
 */
function toYouTubeEmbed(url: string): string | null {
  const match = url.match(
    /(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]+)/,
  )
  return match ? `https://www.youtube.com/embed/${match[1]}` : null
}

/**
 * Bloco "Conheca a marca" do v10. Layout editorial:
 *   h2 "Conheça a marca" (palavra 'marca' italic accent via <em>)
 *   videoFrame 16/9 max-width 900px ink-900 + border ink-500.
 *
 * Comportamento adaptativo:
 *   - YouTube: embed direto via iframe (no autoplay).
 *   - Outras URLs: nao da pra embedar generico (CSP/CORS), entao
 *     renderiza placeholder ink-900 com play button laranja que abre
 *     videoUrl em nova aba.
 *
 * Drop do click-to-play que tinha antes — simplificacao em troca de
 * direct embed (YouTube) e link out (resto). Sem 'use client' agora;
 * componente vira server-rendered.
 *
 * Some o bloco inteiro quando nao ha videoUrl valida.
 */
export default function VideoLanding({ videoUrls }: VideoLandingProps) {
  const url = (videoUrls ?? []).find((u) => u && u.trim())
  if (!url) return null
  const embed = toYouTubeEmbed(url)

  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        Conheça a <em>marca</em>
      </h2>
      <div className={styles.videoFrame}>
        {embed ? (
          <iframe
            src={embed}
            title="Vídeo institucional"
            allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        ) : (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Reproduzir vídeo institucional"
            className={styles.playBtn}
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 16 16"
              style={{ marginLeft: 3 }}
              aria-hidden="true"
            >
              <path d="M3 2L13 8L3 14V2Z" fill="var(--paper-warm)" />
            </svg>
          </a>
        )}
      </div>
    </section>
  )
}
