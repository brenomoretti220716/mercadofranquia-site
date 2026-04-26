import styles from './landing.module.css'

interface GaleriaLandingProps {
  urls?: string[] | null
  /** Limite de tiles renderizados; o sexto vira "+N" se houver excedente. */
  maxTiles?: number
}

/**
 * Bloco "Veja as lojas" do v9. h2 fixo "**Veja** as lojas".
 * Grid 3 colunas (gap 4px), cada item aspect 1. Sexto tile pode virar
 * contador "+N" quando ha mais imagens do que slots. Some se sem fotos.
 */
export default function GaleriaLanding({
  urls,
  maxTiles = 6,
}: GaleriaLandingProps) {
  const valid = (urls ?? []).filter((u) => u && u.trim())
  if (valid.length === 0) return null
  const tiles = valid.slice(0, maxTiles - 1)
  const overflow = valid.length - tiles.length

  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        <span className={styles.accent}>Veja</span> as lojas
      </h2>
      <div className={styles.gallery}>
        {tiles.map((u, i) => (
          <div key={`${i}-${u}`} className={styles.galleryItem}>
            <img src={u} alt={`Foto ${i + 1}`} />
          </div>
        ))}
        {overflow > 0 && (
          <div className={styles.galleryItem}>
            <span className={styles.galleryMore}>+{overflow}</span>
          </div>
        )}
      </div>
    </section>
  )
}
