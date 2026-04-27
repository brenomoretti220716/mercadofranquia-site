import styles from './landing.module.css'

interface BannerLandingProps {
  url?: string | null
  alt?: string
}

/**
 * Banner full-width (240px) — hotfix Fatia 1.8 pos-deploy:
 * skip-if-null. Quando bannerUrl null/empty, retorna null e o bloco
 * some inteiro. Antes renderizava placeholder dark hachurado em
 * todas as 1.404 franquias sem banner em prod — comportamento de
 * mockup que escapou pra producao.
 */
export default function BannerLanding({ url, alt }: BannerLandingProps) {
  if (!url || !url.trim()) return null
  return (
    <div className={`${styles.landing} ${styles.banner}`}>
      <img
        src={url}
        alt={alt ?? 'Banner da franquia'}
        className={styles.bannerImg}
      />
    </div>
  )
}
