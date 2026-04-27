import styles from './landing.module.css'

interface SobreLandingProps {
  description?: string | null
}

/**
 * Bloco "Sobre a marca" do v10. Layout editorial:
 *   kicker "Sobre a marca" -> h2 "Sobre a marca" (palavra 'marca' italic
 *   accent) -> textBlock 16px ink-900 max-width 680px com a description
 *   da Franchise.
 *
 * As metas de ano (Fundada em / Franqueia desde / ABF desde) sairam
 * desse bloco — agora vivem no heroMeta do Hero (junto com Sede e
 * unidades).
 *
 * Some o bloco inteiro quando description vazia/null.
 */
export default function SobreLanding({ description }: SobreLandingProps) {
  if (!description || !description.trim()) return null

  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <div className={styles.kicker}>Sobre a marca</div>
      <h2 className={styles.heading}>
        Sobre a <span className={styles.accent}>marca</span>
      </h2>
      <p className={styles.textBlock}>{description}</p>
    </section>
  )
}
