import styles from './landing.module.css'

interface Selo {
  label: string
  name: string
}

interface SelosStripLandingProps {
  selos?: Selo[] | null
}

/**
 * Strip de selos (ABF Verified, RA 1000, etc). NAO ha modelagem
 * desses dados ainda — Fatia futura. Por enquanto, renderiza apenas
 * se um array nao-vazio for passado externamente; ausente = bloco
 * some completamente.
 */
export default function SelosStripLanding({ selos }: SelosStripLandingProps) {
  if (!selos || selos.length === 0) return null
  return (
    <div className={`${styles.landing} ${styles.selosStrip}`}>
      {selos.map((s, i) => (
        <div key={`${i}-${s.name}`} className={styles.selo}>
          <div className={styles.seloLabel}>{s.label}</div>
          <div className={styles.seloName}>{s.name}</div>
        </div>
      ))}
    </div>
  )
}
