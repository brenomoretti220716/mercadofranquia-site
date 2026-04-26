import styles from './landing.module.css'

interface SobreLandingProps {
  description?: string | null
  /** Ano de fundacao da marca — vai num kicker mono abaixo do paragrafo. */
  brandFoundationYear?: number | null
  /** Ano em que comecou a franquear. */
  franchiseStartYear?: number | null
  /** Ano de associacao a ABF. */
  abfSince?: number | null
}

/**
 * Bloco "Sobre a marca" do v9. h2 fixo "Sobre a **marca**". Renderiza
 * o description da Franchise. Os meta-dados (anos) saem em uma linha
 * mono abaixo, separados por bullet — opcional, some quando todos
 * vazios.
 *
 * Some o bloco inteiro se NAO houver description nem nenhum meta-dado.
 */
export default function SobreLanding({
  description,
  brandFoundationYear,
  franchiseStartYear,
  abfSince,
}: SobreLandingProps) {
  const hasDescription = description && description.trim()
  const metas: string[] = []
  if (brandFoundationYear) metas.push(`Fundada em ${brandFoundationYear}`)
  if (franchiseStartYear) metas.push(`Franqueia desde ${franchiseStartYear}`)
  if (abfSince) metas.push(`ABF desde ${abfSince}`)

  if (!hasDescription && metas.length === 0) return null

  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        Sobre a <span className={styles.accent}>marca</span>
      </h2>
      {hasDescription && <p className={styles.aboutText}>{description}</p>}
      {metas.length > 0 && (
        <p
          className={styles.metricLabel}
          style={{ marginTop: hasDescription ? 16 : 4 }}
        >
          {metas.join(' · ')}
        </p>
      )}
    </section>
  )
}
