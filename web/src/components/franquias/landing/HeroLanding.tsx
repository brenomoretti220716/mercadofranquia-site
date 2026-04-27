import Image from 'next/image'
import { getFranchiseImageUrl } from '@/src/utils/franchiseImageUtils'
import styles from './landing.module.css'

interface HeroLandingProps {
  name: string
  segment?: string | null
  tagline?: string | null
  /** Logo da marca, 80x80 com borda editorial. Some se null/invalido. */
  logoUrl?: string | null
  /** Pra hero-meta "Fundada em {year}". */
  franchiseStartYear?: number | null
  /** Pra hero-meta "Sede {headquarter}, {headquarterState}". */
  headquarter?: string | null
  headquarterState?: string | null
  totalUnits?: number | null
  minimumInvestment?: number | null
  maximumInvestment?: number | null
  minimumReturnOnInvestment?: number | null
  maximumReturnOnInvestment?: number | null
  /** CTA primario "Quero ser franqueado →" rola pro lead form. */
  onCtaClick?: () => void
  /** CTA ghost "Como funciona" rola pro stepper. Opcional. */
  onGhostClick?: () => void
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
  if (a && b && a !== b) {
    // Junta os dois sem repetir o "R$" (R$ 139–342k em vez de R$ 139k–R$ 342k).
    const bSuffix = b.replace(/^R\$\s*/, '')
    return `${a.replace(/k$/, '')}–${bSuffix}`
  }
  return a ?? b ?? '—'
}

function paybackRange(min?: number | null, max?: number | null): string {
  if (min && max && min !== max) return `${min}–${max} meses`
  if (min) return `${min} meses`
  if (max) return `${max} meses`
  return '—'
}

/**
 * Acentua a ultima palavra do nome em italic (Instrument Serif italic
 * laranja) — espelha o "Pizza do <em>João</em>" do mockup v10. Quando
 * o nome eh single-word, retorna sem em (a italica precisa de
 * contraste com texto regular pra funcionar editorialmente).
 */
function renderHeroName(name: string): React.ReactNode {
  const tokens = name.trim().split(/\s+/)
  if (tokens.length <= 1) return name
  const last = tokens[tokens.length - 1]
  const lead = tokens.slice(0, -1).join(' ')
  return (
    <>
      {lead} <em>{last}</em>
    </>
  )
}

/**
 * Hero do v10. Estrutura editorial:
 *   tags row -> kicker "Ficha da rede" -> h1 96px Instrument Serif (com
 *   <em> na ultima palavra) -> tagline -> hero-meta mono uppercase com
 *   3 campos (Fundada em / Sede / unidades) -> KPI strip 3 cols
 *   (Investimento / Payback / Unidades) -> 2 CTAs (laranja primario +
 *   ghost ink-900).
 *
 * Cada elemento condicional some quando o dado nao existe; a moldura
 * (.section) e o titulo (.heroName) sao sempre renderizados.
 *
 * Campos do mockup nao mapeados (pra fatia futura):
 *   - tag verde "Payback baixo" (calculo vs setor)
 *   - hero-meta "Marca registrada" (campo INPI)
 *   - kpiSub "Inclui royalty", "Abaixo da media do setor", "+18 nos
 *     ultimos 12 meses" (sem coluna no DB)
 */
export default function HeroLanding({
  name,
  segment,
  tagline,
  logoUrl,
  franchiseStartYear,
  headquarter,
  headquarterState,
  totalUnits,
  minimumInvestment,
  maximumInvestment,
  minimumReturnOnInvestment,
  maximumReturnOnInvestment,
  onCtaClick,
  onGhostClick,
}: HeroLandingProps) {
  const sedeText =
    headquarter && headquarterState
      ? `${headquarter}, ${headquarterState}`
      : (headquarter ?? headquarterState ?? null)

  // getFranchiseImageUrl valida formato; URLs ja sao absolutas no DB
  // (placehold.co local, S3 em prod). Sem prefixo NEXT_PUBLIC_API_URL.
  const safeLogoUrl = getFranchiseImageUrl(logoUrl)

  return (
    <section className={`${styles.landing} ${styles.section}`}>
      {segment ? (
        <div className={styles.heroTags}>
          <span className={styles.tag}>{segment}</span>
        </div>
      ) : null}

      <div className={styles.kicker}>Ficha da rede</div>

      <div className={styles.heroNameRow}>
        {safeLogoUrl ? (
          <Image
            src={safeLogoUrl}
            alt={name}
            width={96}
            height={96}
            className={styles.heroLogo}
            unoptimized
          />
        ) : null}
        <h1 className={styles.heroName}>{renderHeroName(name)}</h1>
      </div>

      {tagline ? <p className={styles.tagline}>{tagline}</p> : null}

      <div className={styles.heroMeta}>
        {franchiseStartYear ? (
          <span>
            <span>Fundada em</span>
            <b>{franchiseStartYear}</b>
          </span>
        ) : null}
        {sedeText ? (
          <span>
            <span>Sede</span>
            <b>{sedeText}</b>
          </span>
        ) : null}
        {typeof totalUnits === 'number' ? (
          <span>
            <b>{totalUnits.toLocaleString('pt-BR')}</b>
            <span style={{ marginLeft: 6 }}>unidades</span>
          </span>
        ) : null}
      </div>

      <div className={styles.kpiStrip}>
        <div className={styles.kpi}>
          <div className={styles.micro}>Investimento</div>
          <div className={styles.kpiValue}>
            {investmentRange(minimumInvestment, maximumInvestment)}
          </div>
          {/* TODO: kpiSub "Inclui royalty" — campo nao existe no DB. */}
        </div>
        <div className={styles.kpi}>
          <div className={styles.micro}>Payback</div>
          <div className={styles.kpiValue}>
            {paybackRange(minimumReturnOnInvestment, maximumReturnOnInvestment)}
          </div>
        </div>
        <div className={styles.kpi}>
          <div className={styles.micro}>Unidades em operação</div>
          <div className={styles.kpiValue}>
            {typeof totalUnits === 'number'
              ? totalUnits.toLocaleString('pt-BR')
              : '—'}
          </div>
        </div>
      </div>

      <div className={styles.ctaRow}>
        <button type="button" className={styles.cta} onClick={onCtaClick}>
          Quero ser franqueado →
        </button>
        {onGhostClick ? (
          <button
            type="button"
            className={`${styles.cta} ${styles.ctaGhost}`}
            onClick={onGhostClick}
          >
            Como funciona
          </button>
        ) : null}
      </div>
    </section>
  )
}
