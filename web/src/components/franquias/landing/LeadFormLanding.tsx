'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import styles from './landing.module.css'

interface LeadFormLandingProps {
  franchiseName: string
}

/**
 * Bloco final "Quero saber mais" do v9 — secao dark (#0A0B0F) com
 * formulario de captura de lead. h2 fixo "Quero **saber** mais".
 *
 * Submit stub: Fatia 1.5 e visual-only. Backend de leads (Hubspot)
 * ainda nao tem endpoint exposto — submit dispara um toast informando
 * que a feature esta em construcao. Wire-up real entra em fatia
 * dedicada do funil de captura.
 */
export default function LeadFormLanding({
  franchiseName,
}: LeadFormLandingProps) {
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (submitting || submitted) return
    setSubmitting(true)
    // TODO: wire pra backend quando o endpoint /leads existir.
    setTimeout(() => {
      setSubmitting(false)
      setSubmitted(true)
      toast.info(
        'Captura de lead ainda em construção — guardamos seu interesse e a marca entra em contato em breve.',
      )
    }, 600)
  }

  return (
    <section className={`${styles.landing} ${styles.leadSection}`}>
      <div className={styles.leadInner}>
        <div className={styles.leadKicker}>Próximo passo</div>
        <h2 className={styles.leadHeading}>
          Quero <span className={styles.accent}>saber</span> mais
        </h2>
        <p className={styles.leadSub}>
          Preencha e a {franchiseName} entra em contato. Você também recebe a
          análise comparativa da rede no Mercado Franquia.
        </p>

        <form className={styles.leadForm} onSubmit={onSubmit}>
          <input
            type="text"
            name="name"
            placeholder="Nome completo"
            required
            disabled={submitting || submitted}
          />
          <input
            type="email"
            name="email"
            placeholder="E-mail"
            required
            disabled={submitting || submitted}
          />
          <input
            type="tel"
            name="phone"
            placeholder="Telefone com DDD"
            required
            disabled={submitting || submitted}
          />
          <div className={styles.leadFormRow}>
            <input
              type="text"
              name="city"
              placeholder="Cidade"
              disabled={submitting || submitted}
            />
            <input
              type="text"
              name="state"
              placeholder="UF"
              maxLength={2}
              disabled={submitting || submitted}
            />
          </div>
          <select
            name="capital"
            required
            disabled={submitting || submitted}
            defaultValue=""
          >
            <option value="" disabled>
              Capital disponível
            </option>
            <option value="100-300">R$ 100 a 300 mil</option>
            <option value="300-500">R$ 300 a 500 mil</option>
            <option value="500+">Acima de R$ 500 mil</option>
          </select>
          <button
            type="submit"
            className={`${styles.btn} ${styles.btnPrimary}`}
            style={{ marginTop: 8 }}
            disabled={submitting || submitted}
          >
            {submitted
              ? 'Interesse enviado ✓'
              : submitting
                ? 'Enviando...'
                : 'Enviar interesse →'}
          </button>
          <p className={styles.leadDisclaimer}>
            Ao enviar, concordo com os termos e a política de privacidade (LGPD)
          </p>
        </form>
      </div>
    </section>
  )
}
