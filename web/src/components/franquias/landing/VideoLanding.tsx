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
 * Bloco "Conheca a marca" do v9. h2 fixo "Conheca a **marca**".
 * Le franchise.videoUrls (lista parseada do TEXT do banco). Pega o
 * primeiro url; se for YouTube, embed; caso contrario, <video> nativo.
 * Some se nao houver nenhuma url valida.
 */
export default function VideoLanding({ videoUrls }: VideoLandingProps) {
  const url = (videoUrls ?? []).find((u) => u && u.trim())
  if (!url) return null
  const ytId = youtubeIdFromUrl(url)

  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        Conheça a <span className={styles.accent}>marca</span>
      </h2>
      <div className={styles.videoFrame}>
        {ytId ? (
          <iframe
            src={`https://www.youtube.com/embed/${ytId}`}
            title="Vídeo institucional"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        ) : (
          <video src={url} controls preload="metadata" />
        )}
      </div>
    </section>
  )
}
