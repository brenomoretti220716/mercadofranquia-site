import type { BusinessModel } from '@/src/hooks/businessModels/useBusinessModels'
import styles from './landing.module.css'

interface AggregateRange {
  min?: number | null
  max?: number | null
}

interface ModelosLandingProps {
  models?: BusinessModel[] | null
  /**
   * Valores agregados da Franchise pra preencher os cards. Usado em
   * TODOS os cards porque BusinessModel nao tem investment/payback
   * por modelo no DB ainda.
   *
   * TODO (fatia futura): estender BusinessModel com colunas
   * minimumInvestment/maximumInvestment/payback/area pra cada card
   * carregar valores proprios em vez de repetir o agregado.
   */
  aggregateInvestment?: AggregateRange
  aggregatePayback?: AggregateRange
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
 * Bloco "Modelos disponíveis" do v10. Layout editorial:
 *   kicker "Modelos" -> h2 "Modelos disponiveis" (ultima palavra italic
 *   accent) -> grid 3 cols com cards de modelo. Cada card tem
 *   modelName em Instrument Serif 26px + 2 linhas (Investimento /
 *   Payback) com label mono uppercase + value Instrument Serif 17px
 *   tabular.
 *
 * Some o bloco inteiro quando nao ha modelos (drop do fallback do v9
 * que renderizava card unico com agregado da Franchise — agora se nao
 * ha modelos, a secao some e o agregado aparece so na KPI strip do
 * Hero).
 *
 * Campos do mockup nao mapeados:
 *   - tags "Físico/Modular/Compacto" (BusinessModel.category)
 *   - linha "Área" (BusinessModel.area)
 *   - investment/payback per-modelo (BusinessModel.minimumInvestment etc)
 *   Cada card hoje mostra os valores AGREGADOS da Franchise repetidos
 *   ate as colunas existirem no model.
 */
export default function ModelosLanding({
  models,
  aggregateInvestment,
  aggregatePayback,
}: ModelosLandingProps) {
  if (!models || models.length === 0) return null

  const invText = investmentRange(
    aggregateInvestment?.min,
    aggregateInvestment?.max,
  )
  const payText = paybackRange(aggregatePayback?.min, aggregatePayback?.max)

  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <div className={styles.kicker}>Modelos</div>
      <h2 className={styles.heading}>
        Modelos <span className={styles.accent}>disponíveis</span>
      </h2>
      <div className={styles.models}>
        {models.map((m) => (
          <div key={m.id} className={styles.model}>
            <div className={styles.modelHead}>
              <div className={styles.modelName}>{m.name}</div>
            </div>
            <div className={styles.modelRow}>
              <span className={styles.modelRowLabel}>Investimento</span>
              <span className={styles.modelRowValue}>{invText}</span>
            </div>
            <div className={styles.modelRow}>
              <span className={styles.modelRowLabel}>Payback</span>
              <span className={styles.modelRowValue}>{payText}</span>
            </div>
            {/* TODO: linha Area + tags categoria — campos nao existem
                em BusinessModel ainda. */}
          </div>
        ))}
      </div>
    </section>
  )
}
