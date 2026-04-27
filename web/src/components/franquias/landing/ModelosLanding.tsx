import type { BusinessModel } from '@/src/hooks/businessModels/useBusinessModels'
import styles from './landing.module.css'

interface ModelosLandingProps {
  models?: BusinessModel[] | null
  // Cenário A (sem modelos OU modelos sem dado nas 5 metricas-chave) —
  // agregados da Franchise pra ficha tecnica.
  // Cenário B (com modelos populados) le diretamente de cada
  // BusinessModel, ignorando esses props.
  minimumInvestment?: number | null
  maximumInvestment?: number | null
  minimumReturnOnInvestment?: number | null
  maximumReturnOnInvestment?: number | null
  franchiseFee?: number | null
  royalties?: number | null
  advertisingFee?: number | null
  workingCapital?: number | null
  setupCapital?: number | null
  storeArea?: number | null
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
}

/**
 * Constroi as 5 metricas-chave de um BusinessModel — so as linhas com
 * dado entram. Ordem fixa:
 *   1. Investimento
 *   2. Payback
 *   3. Faturamento medio
 *   4. Rentabilidade media
 *   5. Area
 *
 * Os outros campos do BusinessModel (taxa franquia, royalties, propaganda,
 * capital giro, capital instalacao) ficam ocultos da pagina publica nesta
 * fatia. Vao alimentar o sistema de ranges agregados na Fatia 1.9 (ver
 * HANDOFF.md). Continuam sendo coletados pelo editor.
 */
function buildModelRows(m: BusinessModel): RowSpec[] {
  const rows: RowSpec[] = []
  const inv = formatBRL(m.investment)
  if (inv) rows.push({ label: 'Investimento', value: inv })
  if (isPresent(m.payback))
    rows.push({ label: 'Payback', value: `${m.payback} meses` })
  const rev = formatBRL(m.averageMonthlyRevenue)
  if (rev) rows.push({ label: 'Faturamento médio', value: `${rev}/mês` })
  const prof = formatPercent(m.profitability)
  if (prof) rows.push({ label: 'Rentabilidade média', value: prof })
  if (isPresent(m.storeArea))
    rows.push({ label: 'Área', value: `${m.storeArea}m²` })
  return rows
}

function ModelCard({ model }: { model: BusinessModel }) {
  const rows = buildModelRows(model)
  if (rows.length === 0) return null
  return (
    <article className={styles.modelCard}>
      <header className={styles.modelCardHead}>
        <h3 className={styles.modelCardName}>{model.name}</h3>
      </header>
      <dl className={styles.modelCardData}>
        {rows.map((r) => (
          <div key={r.label} className={styles.modelRow}>
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
 * Cenário A — sem businessModels OU modelos todos sem as 5 metricas-chave
 *   populadas: ficha tecnica em tabela editorial usando os agregados da
 *   Franchise (kicker "Investimento" + h2 "Como investir nessa rede"
 *   com 'rede' em italic accent + linhas label-mono / value-serif).
 *   So renderiza linhas com dado.
 *
 * Cenário B — modelos com pelo menos 1 das 5 metricas-chave populada:
 *   cards bege paper-warm flutuando com gap 16px, sem bordas externas.
 *   Cada card mostra ate 5 metricas (Investimento, Payback, Faturamento
 *   medio, Rentabilidade media, Area). data-count no grid faz layout
 *   adaptativo: 1 modelo full-width, 2 em duas cols, 3+ em tres cols.
 *
 * Some o bloco inteiro quando nao ha modelos populados E nenhum agregado
 * da Franchise tem dado.
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
  const visibleModels = (models ?? []).filter(
    (m) => buildModelRows(m).length > 0,
  )
  const hasVisibleModels = visibleModels.length > 0

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

  if (!hasVisibleModels && !hasAnyFinancial) return null

  if (!hasVisibleModels) {
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

  // Cenário B: cards bege flutuando com 5 metricas-chave per modelo.
  // data-count cap em 3: 1 modelo = full, 2 = meio, 3+ = tres cols.
  const dataCount = Math.min(visibleModels.length, 3)

  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <div className={styles.kicker}>Modelos</div>
      <h2 className={styles.heading}>
        Modelos <span className={styles.accent}>disponíveis</span>
      </h2>
      <div className={styles.modelsGrid} data-count={dataCount}>
        {visibleModels.map((m) => (
          <ModelCard key={m.id} model={m} />
        ))}
      </div>
    </section>
  )
}
