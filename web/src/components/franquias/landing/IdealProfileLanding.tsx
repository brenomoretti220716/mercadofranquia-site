import styles from './landing.module.css'

interface IdealProfileLandingProps {
  text?: string | null
}

/**
 * Bloco "Perfil ideal" do v9. Titulo h2 fixo:
 *   "Perfil **ideal**" (ideal em Fraunces italic laranja).
 *
 * Texto livre, paragrafo unico, max-width 580px.
 * Renderiza nada quando text vazio/null.
 */
export default function IdealProfileLanding({ text }: IdealProfileLandingProps) {
  if (!text || !text.trim()) return null
  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        Perfil <span className={styles.accent}>ideal</span>
      </h2>
      <p className={styles.profileText}>{text}</p>
    </section>
  )
}
