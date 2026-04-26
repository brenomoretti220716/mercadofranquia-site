import styles from './landing.module.css'

interface SidebarCTAProps {
  /** Investimento minimo (em reais). Usado pro "a partir de". */
  minimumInvestment?: number | null
  /** Investimento maximo. Quando presente + diferente do min, mostra range. */
  maximumInvestment?: number | null
  /** Payback minimo em meses. */
  minimumReturnOnInvestment?: number | null
  /** Payback maximo em meses. */
  maximumReturnOnInvestment?: number | null
  /** Total de unidades da rede. */
  totalUnits?: number | null
  /** Telefone de contato (vem de franchise.contact?.phone). */
  phone?: string | null
  /** Marca da ABF. */
  isAbfAssociated?: boolean | null
  /** Callback do CTA principal — scroll suave pro lead form. */
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

function investmentSummary(
  min?: number | null,
  max?: number | null,
): { label: string; value: string } {
  const a = formatBRL(min)
  const b = formatBRL(max)
  if (a && b && a !== b) {
    return { label: 'Investimento', value: `${a}–${b}` }
  }
  if (a) return { label: 'Investimento a partir de', value: a }
  if (b) return { label: 'Investimento ate', value: b }
  return { label: 'Investimento', value: 'Sob consulta' }
}

function paybackText(min?: number | null, max?: number | null): string | null {
  if (min && max && min !== max) return `${min}–${max} meses`
  if (min) return `${min} meses`
  if (max) return `${max} meses`
  return null
}

function digitsOnly(s: string): string {
  return s.replace(/\D/g, '')
}

/**
 * Sidebar sticky de conversao — Fatia 1.7. Mostra apenas no desktop
 * ≥ 1024px (escondida via .sidebar em < 1024px); no mobile o CTA
 * primario do Hero cumpre o papel.
 *
 * Decisoes de conteudo (queremos densidade, nao muralha):
 *   1. Investimento (label + valor) — primeiro porque e o qualificador
 *      mais comum dos investidores quando avaliam franquias.
 *   2. CTA orange "Quero ser franqueado →" — mesmo do Hero, scroll
 *      pro LeadForm.
 *   3. "Fale direto" — telefone clicavel (tel:) quando existe. Bloco
 *      escondido inteiro se nao tem telefone (evita texto "—").
 *   4. "Resumo" — payback + unidades em mono (so renderiza linhas que
 *      tem dado real).
 *   5. Selo ABF — bullet verde + "Associada ABF" se isAbfAssociated.
 *
 * NOTAS:
 * - WhatsApp ficou de fora porque Franchise TS type ainda nao tem
 *   esse campo; backend ja retorna desde Fatia 0.5, mas a tipagem
 *   no frontend precisa ser estendida — fatia futura.
 * - Selos extras (RA 1000, B Corp etc.) ainda sem modelagem — fatia
 *   futura.
 */
export default function SidebarCTA({
  minimumInvestment,
  maximumInvestment,
  minimumReturnOnInvestment,
  maximumReturnOnInvestment,
  totalUnits,
  phone,
  isAbfAssociated,
  onCtaClick,
}: SidebarCTAProps) {
  const investment = investmentSummary(minimumInvestment, maximumInvestment)
  const payback = paybackText(
    minimumReturnOnInvestment,
    maximumReturnOnInvestment,
  )
  const phoneDigits = phone ? digitsOnly(phone) : ''
  const hasPhone = phoneDigits.length >= 10
  const hasResumo = payback || typeof totalUnits === 'number'

  return (
    <div className={styles.sidebarCard}>
      <div className={styles.sidebarLabel}>{investment.label}</div>
      <div className={styles.sidebarValue}>{investment.value}</div>

      <button
        type="button"
        className={`${styles.btn} ${styles.btnPrimary} ${styles.sidebarCta}`}
        onClick={onCtaClick}
      >
        Quero ser franqueado →
      </button>

      {hasPhone && (
        <>
          <hr className={styles.sidebarDivider} />
          <div className={styles.sidebarSectionLabel}>Fale direto</div>
          <a className={styles.sidebarLink} href={`tel:${phoneDigits}`}>
            <span>{phone}</span>
            <span className={styles.sidebarLinkArrow}>→</span>
          </a>
        </>
      )}

      {hasResumo && (
        <>
          <hr className={styles.sidebarDivider} />
          <div className={styles.sidebarSectionLabel}>Resumo</div>
          {payback && (
            <div className={styles.sidebarStat}>
              <span className={styles.sidebarStatLabel}>Payback</span>
              <span className={styles.sidebarStatValue}>{payback}</span>
            </div>
          )}
          {typeof totalUnits === 'number' && (
            <div className={styles.sidebarStat}>
              <span className={styles.sidebarStatLabel}>Unidades</span>
              <span className={styles.sidebarStatValue}>
                {totalUnits.toLocaleString('pt-BR')}
              </span>
            </div>
          )}
        </>
      )}

      {isAbfAssociated && (
        <>
          <hr className={styles.sidebarDivider} />
          <div className={styles.sidebarBadge}>Associada ABF</div>
        </>
      )}
    </div>
  )
}
