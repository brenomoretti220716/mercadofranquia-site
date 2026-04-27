import type { ProcessStep } from '@/src/schemas/franchises/Franchise'
import styles from './landing.module.css'

interface ProcessStepperLandingProps {
  steps?: ProcessStep[] | null
}

/**
 * Bloco "Como funciona" do v10. Layout editorial:
 *   h2 "Como funciona" (palavra 'funciona' em italic accent via <em>)
 *   <ol> com cada etapa em <li>:
 *     stepNum (Instrument Serif italic 64px laranja, width 72px)
 *     stepBody com stepTitle (Instrument Serif 24px) + stepDesc
 *     opcional (15px ink-900 line-height 1.55).
 *   Border-bottom 1px ink-300 entre <li>s; ultimo sem border.
 *
 * Numeracao 1-based (idx + 1) — independente de qualquer rotulo no
 * JSON. Description renderiza so quando presente; titulo eh sempre
 * obrigatorio (.title).
 *
 * Some o bloco inteiro quando steps null/empty.
 */
export default function ProcessStepperLanding({
  steps,
}: ProcessStepperLandingProps) {
  if (!steps || steps.length === 0) return null
  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        Como <em>funciona</em>
      </h2>
      <ol className={styles.steps}>
        {steps.map((step, idx) => (
          <li key={`${idx}-${step.title}`} className={styles.step}>
            <div className={styles.stepNum}>{idx + 1}</div>
            <div className={styles.stepBody}>
              <div className={styles.stepTitle}>{step.title}</div>
              {step.description && (
                <div className={styles.stepDesc}>{step.description}</div>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
