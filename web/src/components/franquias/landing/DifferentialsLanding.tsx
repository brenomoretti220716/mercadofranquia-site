import styles from './landing.module.css'

interface DifferentialsLandingProps {
  items?: string[] | null
}

/**
 * Bloco "Diferenciais" do v9. Titulo h2 fixo:
 *   "**Diferenciais**" (a palavra inteira em Fraunces italic laranja).
 *
 * Lista com bullet markers (quadradinhos pretos pequenos), separadores
 * de linha entre itens.
 * Renderiza nada quando items vazio/null.
 */
export default function DifferentialsLanding({
  items,
}: DifferentialsLandingProps) {
  if (!items || items.length === 0) return null
  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        <span className={styles.accent}>Diferenciais</span>
      </h2>
      <ul className={styles.diff}>
        {items.map((item, i) => (
          <li key={`${i}-${item}`} className={styles.diffItem}>
            {item}
          </li>
        ))}
      </ul>
    </section>
  )
}
