import styles from './landing.module.css'

interface HeroTaglineProps {
  tagline?: string | null
}

/**
 * Tagline abaixo do nome no Hero. Cor unica ink, sem Fraunces.
 * Renderiza nada quando vazio — o bloco some.
 */
export default function HeroTagline({ tagline }: HeroTaglineProps) {
  if (!tagline || !tagline.trim()) return null
  return (
    <div className={styles.landing}>
      <p className={styles.tagline}>{tagline}</p>
    </div>
  )
}
