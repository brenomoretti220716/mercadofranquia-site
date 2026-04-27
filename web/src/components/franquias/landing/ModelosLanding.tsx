import type { BusinessModel } from '@/src/hooks/businessModels/useBusinessModels'
import styles from './landing.module.css'

interface ModelosLandingProps {
  models?: BusinessModel[] | null
  // Investimento (REAIS)
  minimumInvestment?: number | null
  maximumInvestment?: number | null
  // ROI/Payback (meses)
  minimumReturnOnInvestment?: number | null
  maximumReturnOnInvestment?: number | null
  // Demais campos financeiros da Franchise
  franchiseFee?: number | null
  royalties?: number | null // %
  advertisingFee?: number | null // %
  workingCapital?: number | null
  storeArea?: number | null // m²
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

function formatPercent(n?: number | null): string | null {
  if (n === null || n === undefined) return null
  return `${n}%`
}

function isPresent(v: number | null | undefined): v is number {
  return v !== null && v !== undefined
}

/**
 * Bloco adaptativo de modelos / investimento.
 *
 * Cenário A — sem businessModels: ficha tecnica em tabela editorial
 *   (kicker "Investimento" + h2 "Como investir nessa rede" com 'rede'
 *   em italic accent + linhas label-mono / value-serif). So renderiza
 *   linhas com dado.
 *
 * Cenário B — com businessModels: grid 3 cols com cards (modelName
 *   Instrument Serif 26px, 2 linhas Investimento/Payback usando o
 *   agregado da Franchise repetido — TODO: per-model quando o backend
 *   tiver colunas dedicadas) + footer "Royalties globais" abaixo do
 *   grid (royalties %, propaganda %, capital de giro).
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

  // Cenário B: cards + footer royalties globais.
  const invText = investmentRange(minimumInvestment, maximumInvestment)
  const payText = paybackRange(
    minimumReturnOnInvestment,
    maximumReturnOnInvestment,
  )

  // Footer royalties globais — monta partes filtradas por presenca.
  const footerParts: string[] = []
  if (isPresent(royalties))
    footerParts.push(`Royalties: ${formatPercent(royalties)}`)
  if (isPresent(advertisingFee))
    footerParts.push(`Propaganda: ${formatPercent(advertisingFee)}`)
  if (isPresent(workingCapital))
    footerParts.push(`Capital de giro: ${formatBRL(workingCapital)}`)
  const hasFooter = footerParts.length > 0

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

      {hasFooter && (
        <div className={styles.modelsFooter}>
          <div className={styles.modelsFooterLabel}>Royalties globais</div>
          <div className={styles.modelsFooterText}>
            {footerParts.join(' · ')}
          </div>
        </div>
      )}
    </section>
  )
}
