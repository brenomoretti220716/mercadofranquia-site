import styles from './landing.module.css'

interface BannerLandingProps {
  url?: string | null
  alt?: string
}

/**
 * Banner full-width (240px) — handoff editorial v10. Quando bannerUrl
 * eh null, renderiza placeholder hachurado (linhas laranja 8% sobre
 * ink-900) com texto mono uppercase. Bloco nunca some — espaco
 * preservado ate o franqueador subir o asset.
 */
export default function BannerLanding({ url, alt }: BannerLandingProps) {
  return (
    <div className={`${styles.landing} ${styles.banner}`}>
      {url ? (
        <img
          src={url}
          alt={alt ?? 'Banner da franquia'}
          className={styles.bannerImg}
        />
      ) : (
        <div className={styles.bannerText}>
          <div>Banner full-width</div>
          <em>1920 × 600 — Capa visual da marca</em>
        </div>
      )}
    </div>
  )
}
