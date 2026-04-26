import styles from './landing.module.css'

interface BannerLandingProps {
  url?: string | null
  alt?: string
}

/**
 * Banner full-width (240px). Quando bannerUrl e null, renderiza
 * placeholder hachurado da paleta v9 — o bloco NAO some, ele apenas
 * fica com aspecto generico ate o franqueador subir o asset.
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
