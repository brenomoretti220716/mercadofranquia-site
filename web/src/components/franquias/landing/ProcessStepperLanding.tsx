import type { ProcessStep } from '@/src/schemas/franchises/Franchise'
import styles from './landing.module.css'

interface ProcessStepperLandingProps {
  steps?: ProcessStep[] | null
}

/**
 * Bloco "Como funciona" do v10. Layout editorial:
 *   kicker "Processo" -> h2 "Como funciona" (palavra 'funciona'
 *   italic accent) -> .steps com cada etapa em row:
 *     stepNum (Instrument Serif italic 64px laranja, width 72px)
 *     stepBody com stepTitle (Instrument Serif 24px) + stepDesc
 *     (15px ink-900 line-height 1.55).
 *   Border-bottom 1px ink-300 entre steps; ultimo sem border.
 *
 * Some o bloco inteiro quando steps null/empty. Numeracao 1-based
 * automatica (nao depende do JSON).
 */
export default function ProcessStepperLanding({
  steps,
}: ProcessStepperLandingProps) {
  if (!steps || steps.length === 0) return null
  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        Como <span className={styles.accent}>funciona</span>
      </h2>
      <div className={styles.steps}>
        {steps.map((step, i) => (
          <div key={`${i}-${step.title}`} className={styles.step}>
            <div className={styles.stepNum}>{i + 1}</div>
            <div className={styles.stepBody}>
              <h3 className={styles.stepTitle}>{step.title}</h3>
              <p className={styles.stepDesc}>{step.description}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
