import styles from './landing.module.css'

interface SobreLandingProps {
  description?: string | null
}

/**
 * Bloco "Sobre a marca" do v9. h2 fixo "Sobre a **marca**".
 * Renderiza o description da Franchise. Some se vazio.
 */
export default function SobreLanding({ description }: SobreLandingProps) {
  if (!description || !description.trim()) return null
  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        Sobre a <span className={styles.accent}>marca</span>
      </h2>
      <p className={styles.aboutText}>{description}</p>
    </section>
  )
}
