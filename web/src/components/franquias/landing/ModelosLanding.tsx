import type { BusinessModel } from '@/src/hooks/businessModels/useBusinessModels'
import styles from './landing.module.css'

interface FranchiseLikeForFallback {
  minimumInvestment?: number | null
  maximumInvestment?: number | null
  franchiseFee?: number | null
  minimumReturnOnInvestment?: number | null
  maximumReturnOnInvestment?: number | null
}

interface ModelosLandingProps {
  models?: BusinessModel[] | null
  /**
   * Fallback usado quando a franquia tem 0 modelos: monta um cardzinho
   * unico com os numeros diretos da Franchise.
   */
  franchiseFallback?: FranchiseLikeForFallback
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
  return a ?? b ?? '—'
}

/**
 * Bloco "Modelos disponiveis" do v9. Comportamento adaptativo:
 *
 * - 0 modelos cadastrados: bloco fica oculto se a Franchise tambem
 *   nao tem investimento direto. Caso contrario, renderiza um card
 *   unico "Investimento" com os valores agregados da propria
 *   Franchise.
 * - 1+ modelos: cards lado a lado com nome + descricao do modelo.
 *
 * NOTA tecnica: a interface BusinessModel atual nao tem investment
 * nem payback por modelo (so name/description/photoUrl). O mockup v9
 * pede esses numeros por modelo — fatia futura precisa estender o
 * model BusinessModel pra carregar esses campos. Por ora, renderizo
 * name + description nos cards.
 */
export default function ModelosLanding({
  models,
  franchiseFallback,
}: ModelosLandingProps) {
  const hasModels = models && models.length > 0

  if (!hasModels) {
    const inv = investmentRange(
      franchiseFallback?.minimumInvestment,
      franchiseFallback?.maximumInvestment,
    )
    const fee = formatBRL(franchiseFallback?.franchiseFee)
    if (inv === '—' && !fee) return null
    return (
      <section className={`${styles.landing} ${styles.section}`}>
        <h2 className={styles.heading}>
          <span className={styles.accent}>Investimento</span>
        </h2>
        <div className={styles.models} style={{ gridTemplateColumns: '1fr' }}>
          <div className={styles.model}>
            {inv !== '—' && (
              <div className={styles.modelRow}>
                <span className={styles.modelLabel}>Investimento total</span>
                <span className={styles.modelValue}>{inv}</span>
              </div>
            )}
            {fee && (
              <div className={styles.modelRow}>
                <span className={styles.modelLabel}>Taxa de franquia</span>
                <span className={styles.modelValue}>{fee}</span>
              </div>
            )}
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        Modelos <span className={styles.accent}>disponíveis</span>
      </h2>
      <div className={styles.models}>
        {models.map((m) => (
          <div key={m.id} className={styles.model}>
            <div className={styles.modelName}>{m.name}</div>
            <div className={styles.modelRow}>
              <span
                className={styles.modelValue}
                style={{ fontSize: 13, fontWeight: 400 }}
              >
                {m.description}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
