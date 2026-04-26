import type { ProcessStep } from '@/src/schemas/franchises/Franchise'
import styles from './landing.module.css'

interface ProcessStepperLandingProps {
  steps?: ProcessStep[] | null
}

/**
 * Bloco "Como funciona" do v9. Titulo h2 fixo:
 *   "Como **funciona**" (funciona em Fraunces italic laranja).
 *
 * Numeros das etapas em Fraunces italic laranja, 32px.
 * Renderiza nada quando steps vazio/null.
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
