'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import styles from './landing.module.css'

interface LeadFormLandingProps {
  franchiseName: string
  franchiseSegment?: string | null
}

/**
 * Bloco final "Quero saber mais" do v10 — secao dark com layout grid
 * 2 colunas:
 *   - Esquerda: kicker "Próximo passo" + h2 56px Instrument Serif
 *     ("saber" italic accent) + intro 15px + bullets editoriais
 *     Direto/Análise/LGPD com label mono uppercase em accent + texto
 *     interpolado com nome/segmento da franquia.
 *   - Direita: form com Nome / E-mail / Telefone / [Cidade UF] /
 *     Capital select / submit ctaBlock + disclaimer mono.
 *
 * Apos submit bem-sucedido, o form some e a coluna direita mostra
 * "Recebemos seu interesse" em Instrument Serif 28px + sub mono
 * uppercase com fallback "A {nome} entra em contato em breve."
 *
 * Submit ainda eh stub — backend de leads (Hubspot) sera ligado em
 * fatia dedicada. Por enquanto dispara toast pra deixar claro pro
 * usuario que o lead nao foi entregue ainda.
 *
 * Bullets seguem a Versão D (honesta):
 *   Direto    — "Seus dados vão à {nome}, sem intermediários"
 *   Análise   — "Comparativo das franquias do segmento {segmento}"
 *               (fallback "do mesmo segmento" se segmento null)
 *   LGPD      — "Sem spam, sem compromisso, sem taxa de cadastro"
 */
export default function LeadFormLanding({
  franchiseName,
  franchiseSegment,
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

  const segmentText = franchiseSegment?.trim()
    ? `Comparativo das franquias do segmento ${franchiseSegment}`
    : 'Comparativo das franquias do mesmo segmento'

  return (
    <section className={`${styles.landing} ${styles.leadSection}`}>
      <div className={styles.leadGrid}>
        <div className={styles.leadLeft}>
          <span className={styles.kicker}>Próximo passo</span>
          <h2 className={styles.leadH2}>
            Quero <em>saber</em> mais
          </h2>
          <p className={styles.leadIntro}>
            Preencha e a {franchiseName} recebe seu interesse. Você também
            recebe a análise comparativa do segmento{' '}
            {franchiseSegment?.trim() ?? 'da rede'} no Mercado Franquia.
          </p>

          <ul className={styles.leadBullets}>
            <li>
              <b>Direto</b>
              <span>Seus dados vão à {franchiseName}, sem intermediários</span>
            </li>
            <li>
              <b>Análise</b>
              <span>{segmentText}</span>
            </li>
            <li>
              <b>LGPD</b>
              <span>Sem spam, sem compromisso, sem taxa de cadastro</span>
            </li>
          </ul>
        </div>

        {submitted ? (
          <div className={styles.leadSuccess}>
            <h3 className={styles.leadSuccessHeading}>
              Recebemos seu interesse
            </h3>
            <p className={styles.leadSuccessSub}>
              A {franchiseName} entra em contato em breve
            </p>
          </div>
        ) : (
          <form className={styles.leadForm} onSubmit={onSubmit}>
            <input
              type="text"
              name="name"
              placeholder="Nome completo"
              required
              disabled={submitting}
            />
            <input
              type="email"
              name="email"
              placeholder="E-mail"
              required
              disabled={submitting}
            />
            <input
              type="tel"
              name="phone"
              placeholder="Telefone com DDD"
              required
              disabled={submitting}
            />
            <div className={styles.leadRow}>
              <input
                type="text"
                name="city"
                placeholder="Cidade"
                required
                disabled={submitting}
              />
              <input
                type="text"
                name="state"
                placeholder="UF"
                maxLength={2}
                required
                disabled={submitting}
              />
            </div>
            <select
              name="capital"
              required
              defaultValue=""
              disabled={submitting}
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
              className={styles.ctaBlock}
              disabled={submitting}
            >
              {submitting ? 'Enviando...' : 'Enviar interesse →'}
            </button>
            <div className={styles.leadDisclaimer}>
              Apenas a {franchiseName} recebe seus dados · Sem intermediários ·
              LGPD
            </div>
          </form>
        )}
      </div>
    </section>
  )
}
