import HeroTagline from './HeroTagline'
import styles from './landing.module.css'

interface HeroLandingProps {
  name: string
  segment?: string | null
  tagline?: string | null
  logoUrl?: string | null
  minimumInvestment?: number | null
  maximumInvestment?: number | null
  minimumReturnOnInvestment?: number | null
  maximumReturnOnInvestment?: number | null
  totalUnits?: number | null
  onCtaClick?: () => void
}

function formatBRL(n?: number | null): string | null {
  if (n === null || n === undefined) return null
  if (n >= 1000) {
    const k = n / 1000
    return `R$ ${k % 1 === 0 ? k.toFixed(0) : k.toFixed(1)}k`
  }
  return `R$ ${n.toFixed(0)}`
}

function investmentRange(min?: number | null, max?: number | null): string {
  const a = formatBRL(min)
  const b = formatBRL(max)
  if (a && b && a !== b) return `${a}–${b}`
  if (a) return a
  if (b) return b
  return '—'
}

function paybackRange(min?: number | null, max?: number | null): string {
  if (min && max && min !== max) return `${min}–${max} meses`
  if (min) return `${min} meses`
  if (max) return `${max} meses`
  return '—'
}

/**
 * Hero do v9: logo + segmento (kicker) + nome (h1) + tagline +
 * 3 metricas (Investimento, Payback, Unidades) + CTA primario laranja.
 *
 * Condicionalidades por elemento:
 * - segmento: omite kicker se ausente
 * - logo: placeholder "LOGO" mono se ausente (mantém estrutura visual)
 * - tagline: HeroTagline ja decide se renderiza
 * - metricas: cada uma cai pra "—" quando dado ausente
 */
export default function HeroLanding({
  name,
  segment,
  tagline,
  logoUrl,
  minimumInvestment,
  maximumInvestment,
  minimumReturnOnInvestment,
  maximumReturnOnInvestment,
  totalUnits,
  onCtaClick,
}: HeroLandingProps) {
  return (
    <div className={`${styles.landing} ${styles.hero}`}>
      <div className={styles.heroTop}>
        <div className={styles.heroLogo}>
          {logoUrl ? <img src={logoUrl} alt={`Logo ${name}`} /> : 'LOGO'}
        </div>
        <div className={styles.heroId}>
          {segment ? <div className={styles.heroSegment}>{segment}</div> : null}
          <h1 className={styles.heroH1}>{name}</h1>
        </div>
      </div>

      <HeroTagline tagline={tagline} />

      <div className={styles.metrics}>
        <div className={styles.metric}>
          <div className={styles.metricLabel}>Investimento</div>
          <div className={styles.metricValue}>
            {investmentRange(minimumInvestment, maximumInvestment)}
          </div>
        </div>
        <div className={styles.metric}>
          <div className={styles.metricLabel}>Payback</div>
          <div className={styles.metricValue}>
            {paybackRange(minimumReturnOnInvestment, maximumReturnOnInvestment)}
          </div>
        </div>
        <div className={styles.metric}>
          <div className={styles.metricLabel}>Unidades</div>
          <div className={styles.metricValue}>
            {typeof totalUnits === 'number'
              ? totalUnits.toLocaleString('pt-BR')
              : '—'}
          </div>
        </div>
      </div>

      <button
        type="button"
        className={`${styles.btn} ${styles.btnPrimary}`}
        onClick={onCtaClick}
      >
        Quero ser franqueado →
      </button>
    </div>
  )
}
