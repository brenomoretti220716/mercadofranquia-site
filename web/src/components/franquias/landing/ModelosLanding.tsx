import type { BusinessModel } from '@/src/hooks/businessModels/useBusinessModels'
import styles from './landing.module.css'

interface ModelosLandingProps {
  models?: BusinessModel[] | null
  // Cenário A (sem modelos) — agregados da Franchise pra ficha tecnica.
  // Cenário B (com modelos) le diretamente de cada BusinessModel,
  // ignorando esses props.
  minimumInvestment?: number | null
  maximumInvestment?: number | null
  minimumReturnOnInvestment?: number | null
  maximumReturnOnInvestment?: number | null
  franchiseFee?: number | null
  royalties?: number | null // %
  advertisingFee?: number | null // %
  workingCapital?: number | null
  setupCapital?: number | null
  storeArea?: number | null // m²
}

function formatBRL(n?: number | null): string | null {
  if (n === null || n === undefined) return null
  if (n >= 1_000_000) {
    const m = n / 1_000_000
    return `R$ ${m % 1 === 0 ? m.toFixed(0) : m.toFixed(1)}M`
  }
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

function formatPercent(n?: number | null): string | null {
  if (n === null || n === undefined) return null
  return `${n}%`
}

function isPresent(v: number | null | undefined): v is number {
  return v !== null && v !== undefined
}

interface RowSpec {
  label: string
  value: string
  primary?: boolean
}

/**
 * Monta a sequencia de rows pra um BusinessModel — so as linhas com
 * dado entram. Order: 4 metricas operacionais primary (investment,
 * payback, faturamento, area) + 5 financeiras secundarias (taxa de
 * franquia, royalties, propaganda, capital de giro, capital de
 * instalacao). Cards com todos os campos null entregam array vazio
 * — caller decide se renderiza o card mesmo assim ou pula.
 */
function buildModelRows(m: BusinessModel): RowSpec[] {
  const rows: RowSpec[] = []
  const inv = formatBRL(m.investment)
  if (inv) rows.push({ label: 'Investimento', value: inv, primary: true })
  if (isPresent(m.payback))
    rows.push({ label: 'Payback', value: `${m.payback} meses`, primary: true })
  const rev = formatBRL(m.averageMonthlyRevenue)
  if (rev)
    rows.push({
      label: 'Faturamento médio',
      value: `${rev}/mês`,
      primary: true,
    })
  if (isPresent(m.storeArea))
    rows.push({ label: 'Área', value: `${m.storeArea}m²`, primary: true })

  const fee = formatBRL(m.franchiseFee)
  if (fee) rows.push({ label: 'Taxa de franquia', value: fee })
  const royaltiesText = formatPercent(m.royalties)
  if (royaltiesText) rows.push({ label: 'Royalties', value: royaltiesText })
  const adFeeText = formatPercent(m.advertisingFee)
  if (adFeeText) rows.push({ label: 'Taxa de propaganda', value: adFeeText })
  const wc = formatBRL(m.workingCapital)
  if (wc) rows.push({ label: 'Capital de giro', value: wc })
  const sc = formatBRL(m.setupCapital)
  if (sc) rows.push({ label: 'Capital de instalação', value: sc })

  return rows
}

function ModelCard({ model }: { model: BusinessModel }) {
  const rows = buildModelRows(model)
  return (
    <article className={styles.modelCard}>
      <header className={styles.modelCardHead}>
        <h3 className={styles.modelCardName}>{model.name}</h3>
      </header>
      <dl className={styles.modelCardData}>
        {rows.map((r) => (
          <div
            key={r.label}
            className={
              r.primary
                ? `${styles.modelRow} ${styles.modelRowPrimary}`
                : styles.modelRow
            }
          >
            <dt>{r.label}</dt>
            <dd>{r.value}</dd>
          </div>
        ))}
      </dl>
    </article>
  )
}

/**
 * Bloco adaptativo de modelos / investimento.
 *
 * Cenário A — sem businessModels: ficha tecnica em tabela editorial
 *   (kicker "Investimento" + h2 "Como investir nessa rede" com 'rede'
 *   em italic accent + linhas label-mono / value-serif). So renderiza
 *   linhas com dado.
 *
 * Cenário B — com businessModels: cards bege paper-warm flutuando com
 *   gap 16px, sem bordas externas. Cada card tem 4 metricas primary
 *   (Investimento, Payback, Faturamento, Area) + ate 5 financeiras
 *   secundarias (Taxa de franquia, Royalties, Propaganda, Capital de
 *   giro, Capital de instalacao). Footer de royalties globais NAO
 *   existe mais — cada card tem royalties proprio.
 *
 * Some o bloco inteiro quando nao ha modelos E nenhum campo financeiro
 * tem dado.
 */
export default function ModelosLanding({
  models,
  minimumInvestment,
  maximumInvestment,
  minimumReturnOnInvestment,
  maximumReturnOnInvestment,
  franchiseFee,
  royalties,
  advertisingFee,
  workingCapital,
  setupCapital,
  storeArea,
}: ModelosLandingProps) {
  const hasModels = models !== null && models !== undefined && models.length > 0

  const hasAnyFinancial =
    isPresent(minimumInvestment) ||
    isPresent(maximumInvestment) ||
    isPresent(minimumReturnOnInvestment) ||
    isPresent(maximumReturnOnInvestment) ||
    isPresent(franchiseFee) ||
    isPresent(royalties) ||
    isPresent(advertisingFee) ||
    isPresent(workingCapital) ||
    isPresent(storeArea)

  if (!hasModels && !hasAnyFinancial) return null

  if (!hasModels) {
    // Cenário A: ficha tecnica
    return (
      <section className={`${styles.landing} ${styles.section}`}>
        <div className={styles.kicker}>Investimento</div>
        <h2 className={styles.heading}>
          Como investir nessa <span className={styles.accent}>rede</span>
        </h2>
        <div className={styles.investimentoTable}>
          {(isPresent(minimumInvestment) || isPresent(maximumInvestment)) && (
            <div className={styles.investimentoRow}>
              <span className={styles.investimentoLabel}>
                Investimento inicial
              </span>
              <span className={styles.investimentoValue}>
                {investmentRange(minimumInvestment, maximumInvestment)}
              </span>
            </div>
          )}
          {isPresent(franchiseFee) && (
            <div className={styles.investimentoRow}>
              <span className={styles.investimentoLabel}>Taxa de franquia</span>
              <span className={styles.investimentoValue}>
                {formatBRL(franchiseFee)}
              </span>
            </div>
          )}
          {isPresent(royalties) && (
            <div className={styles.investimentoRow}>
              <span className={styles.investimentoLabel}>Royalties</span>
              <span className={styles.investimentoValue}>
                {formatPercent(royalties)} sobre faturamento
              </span>
            </div>
          )}
          {isPresent(advertisingFee) && (
            <div className={styles.investimentoRow}>
              <span className={styles.investimentoLabel}>
                Taxa de propaganda
              </span>
              <span className={styles.investimentoValue}>
                {formatPercent(advertisingFee)} sobre faturamento
              </span>
            </div>
          )}
          {isPresent(workingCapital) && (
            <div className={styles.investimentoRow}>
              <span className={styles.investimentoLabel}>Capital de giro</span>
              <span className={styles.investimentoValue}>
                {formatBRL(workingCapital)}
              </span>
            </div>
          )}
          {(isPresent(minimumReturnOnInvestment) ||
            isPresent(maximumReturnOnInvestment)) && (
            <div className={styles.investimentoRow}>
              <span className={styles.investimentoLabel}>Payback</span>
              <span className={styles.investimentoValue}>
                {paybackRange(
                  minimumReturnOnInvestment,
                  maximumReturnOnInvestment,
                )}
              </span>
            </div>
          )}
          {isPresent(storeArea) && (
            <div className={styles.investimentoRow}>
              <span className={styles.investimentoLabel}>Área necessária</span>
              <span className={styles.investimentoValue}>{storeArea}m²</span>
            </div>
          )}
        </div>
      </section>
    )
  }

  // Cenário B: cards bege flutuando com dataset financeiro per-card.
  // Footer de royalties globais foi dropado — cada card carrega o
  // proprio royalties no dataset secundario.
  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <div className={styles.kicker}>Modelos</div>
      <h2 className={styles.heading}>
        Modelos <span className={styles.accent}>disponíveis</span>
      </h2>
      <div className={styles.modelsGrid}>
        {models.map((m) => (
          <ModelCard key={m.id} model={m} />
        ))}
      </div>
    </section>
  )
}
