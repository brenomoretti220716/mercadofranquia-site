import type { Franchise } from '@/src/schemas/franchises/Franchise'
import styles from './landing.module.css'

interface ContactBlockProps {
  franchise: Franchise
}

const onlyDigits = (s: string) => s.replace(/\D/g, '')
const cleanUrl = (s: string) =>
  s
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .replace(/\/$/, '')

interface Channel {
  label: string
  value: string
  href: string
  external: boolean
}

/**
 * Bloco final "Contato direto" — substitui o LeadFormLanding (Fatia 1.9).
 *
 * Renderiza ate 7 canais empilhados (phone, whatsapp, email, website,
 * instagram, facebook, linkedin) com fallback Franchise direto >
 * ContactInfo legado:
 *   phone   = franchise.phone || franchise.contact?.phone
 *   email   = franchise.publicEmail || franchise.contact?.email
 *   website = franchise.contact?.website  (so ContactInfo)
 *   social  = so campos diretos da Franchise
 *
 * scrapedWebsite ignorado (e portal ABF, nao site oficial).
 *
 * Estado vazio (nenhum canal preenchido): kicker "Em breve" + h2 +
 * texto editorial + CTA pra captacao em /anuncie-sua-franquia/cadastro.
 *
 * Mantem paleta dark v10 do .leadSection original (ink-900 + paper-warm
 * + accent #ff8a5c). Coluna unica empilhada — sem narrativa lateral.
 */
export default function ContactBlock({ franchise }: ContactBlockProps) {
  const phone = franchise.phone || franchise.contact?.phone
  const whatsapp = franchise.whatsapp
  const email = franchise.publicEmail || franchise.contact?.email
  const website = franchise.contact?.website
  const instagram = franchise.instagramUrl
  const facebook = franchise.facebookUrl
  const linkedin = franchise.linkedinUrl

  const channels: Channel[] = [
    phone && {
      label: 'Telefone',
      value: phone,
      href: `tel:+55${onlyDigits(phone)}`,
      external: false,
    },
    whatsapp && {
      label: 'WhatsApp',
      value: whatsapp,
      href: `https://wa.me/55${onlyDigits(whatsapp)}`,
      external: true,
    },
    email && {
      label: 'E-mail',
      value: email,
      href: `mailto:${email}`,
      external: false,
    },
    website && {
      label: 'Site',
      value: cleanUrl(website),
      href: website,
      external: true,
    },
    instagram && {
      label: 'Instagram',
      value: cleanUrl(instagram),
      href: instagram,
      external: true,
    },
    facebook && {
      label: 'Facebook',
      value: cleanUrl(facebook),
      href: facebook,
      external: true,
    },
    linkedin && {
      label: 'LinkedIn',
      value: cleanUrl(linkedin),
      href: linkedin,
      external: true,
    },
  ].filter(Boolean) as Channel[]

  if (channels.length === 0) {
    return (
      <section className={`${styles.landing} ${styles.contactSection}`}>
        <div className={styles.contactInner}>
          <span className={styles.kicker}>Em breve</span>
          <h2 className={styles.contactH2}>
            Esta marca ainda não tem <em>contatos diretos</em>
          </h2>
          <p className={styles.contactEmptyText}>
            Investidores chegam até aqui buscando como falar com você. Cadastre
            sua marca e abra o canal direto.
          </p>
          <a
            className={styles.ctaBlock}
            href={`/anuncie-sua-franquia/cadastro?slug=${franchise.slug}`}
          >
            Cadastrar minha marca →
          </a>
        </div>
      </section>
    )
  }

  return (
    <section className={`${styles.landing} ${styles.contactSection}`}>
      <div className={styles.contactInner}>
        <span className={styles.kicker}>Falar com a marca</span>
        <h2 className={styles.contactH2}>
          Contato <em>direto</em>
        </h2>
        <ul className={styles.channels}>
          {channels.map((c) => (
            <li key={c.label} className={styles.channel}>
              <a
                className={styles.channelLink}
                href={c.href}
                {...(c.external
                  ? { target: '_blank', rel: 'noopener noreferrer' }
                  : {})}
              >
                <span className={styles.channelLabel}>{c.label}</span>
                <span className={styles.channelValue}>{c.value}</span>
              </a>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
