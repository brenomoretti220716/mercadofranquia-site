import styles from './landing.module.css'

interface ContactFooterLandingProps {
  phone?: string | null
  email?: string | null
  website?: string | null
}

/**
 * Bloco footer com canais de contato da Franchise. h2 fixo
 * "**Canais** de contato". Renderiza so as linhas que tem dado.
 *
 * Some o bloco inteiro quando todos os 3 sao vazios. Por enquanto le
 * franchise.contact (ContactInfo); fatia futura pode estender pra
 * publicEmail / whatsapp / redes sociais (que ja estao no backend
 * desde Fatia 0.5 mas ainda nao sao expostos no Franchise TS type).
 */
export default function ContactFooterLanding({
  phone,
  email,
  website,
}: ContactFooterLandingProps) {
  const hasAny =
    (phone && phone.trim()) ||
    (email && email.trim()) ||
    (website && website.trim())
  if (!hasAny) return null
  return (
    <section className={`${styles.landing} ${styles.section}`}>
      <h2 className={styles.heading}>
        <span className={styles.accent}>Canais</span> de contato
      </h2>
      <ul style={{ listStyle: 'none', padding: 0, margin: '16px 0 0' }}>
        {website && website.trim() && (
          <li
            style={{ padding: '12px 0', borderBottom: '1px solid var(--line)' }}
          >
            <span className={styles.metricLabel}>Site</span>
            <a
              href={website}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'block',
                fontSize: 15,
                fontWeight: 500,
                color: 'var(--ink)',
                textDecoration: 'underline',
                marginTop: 4,
                wordBreak: 'break-all',
              }}
            >
              {website}
            </a>
          </li>
        )}
        {phone && phone.trim() && (
          <li
            style={{ padding: '12px 0', borderBottom: '1px solid var(--line)' }}
          >
            <span className={styles.metricLabel}>Telefone</span>
            <span
              style={{
                display: 'block',
                fontSize: 15,
                fontWeight: 500,
                marginTop: 4,
              }}
            >
              {phone}
            </span>
          </li>
        )}
        {email && email.trim() && (
          <li style={{ padding: '12px 0' }}>
            <span className={styles.metricLabel}>E-mail</span>
            <a
              href={`mailto:${email}`}
              style={{
                display: 'block',
                fontSize: 15,
                fontWeight: 500,
                color: 'var(--ink)',
                textDecoration: 'underline',
                marginTop: 4,
              }}
            >
              {email}
            </a>
          </li>
        )}
      </ul>
    </section>
  )
}
