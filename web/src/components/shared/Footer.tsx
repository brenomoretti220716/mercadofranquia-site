'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { useAuthContext } from '@/src/hooks/users/useAuth'
import FacebookIcon from '../icons/facebookIcon'
import InstagramIcon from '../icons/instagramIcon'
import LinkedinIcon from '../icons/linkedinIcon'
import YoutubeIcon from '../icons/youtubeIcon'

const footerLinks = {
  franquias: [
    { label: 'Ranking de franquias', href: '/ranking?ratingSort=desc#ranking' },
    { label: 'Todas as franquias', href: '/ranking?nameSort=asc#ranking' },
    { label: 'Por segmento', href: '/ranking?segment=Alimentação#ranking' },
    { label: 'Por investimento', href: '/ranking?investmentSort=asc#ranking' },
  ],
  suporte: [{ label: 'Termos de uso', href: '/termos' }],
}

export default function Footer() {
  const { isAuthenticated } = useAuthContext()
  const router = useRouter()
  const [email, setEmail] = useState('')

  const handleNewsletterSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (email) {
      router.push(`/cadastro?email=${encodeURIComponent(email)}`)
    }
  }

  return (
    <footer className="bg-navy text-white/90">
      {/* CTA "Anuncie sua franquia" — topo, destaque */}
      <div className="bg-[#111111] border-b border-white/10">
        <div className="container py-10 md:py-12">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6 text-center md:text-left">
            <div>
              <h2 className="text-2xl md:text-3xl font-bold text-white mb-2">
                É dono de uma franquia?
              </h2>
              <p className="text-white/70 text-base md:text-lg">
                Anuncie no maior portal de franquias do Brasil
              </p>
            </div>
            <Link
              href="/anuncie-sua-franquia"
              className="inline-flex items-center justify-center px-6 py-3 rounded-full bg-[#E25E3E] hover:bg-[#c04e2e] text-white font-semibold text-base whitespace-nowrap transition-colors shrink-0"
            >
              Anuncie sua franquia grátis
            </Link>
          </div>
        </div>
      </div>

      <div className="container py-16">
        {/* Newsletter — só se não autenticado */}
        {!isAuthenticated && (
          <div className="mb-12 pb-12 border-b border-white/10">
            <div className="flex flex-col md:flex-row items-center justify-between gap-8">
              <div className="text-center md:text-left">
                <h2 className="text-xl md:text-2xl font-semibold text-white mb-2">
                  Receba novidades do mercado de franquias
                </h2>
                <p className="text-white/60 text-sm">
                  Inscreva-se e receba as melhores oportunidades diretamente no
                  seu e-mail.
                </p>
              </div>

              <form
                onSubmit={handleNewsletterSubmit}
                className="flex flex-col sm:flex-row gap-3 w-full md:w-auto"
              >
                <input
                  type="email"
                  placeholder="seu@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-white/10 border border-white/20 text-white placeholder:text-white/40 min-w-[240px] px-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  required
                />
                <button
                  type="submit"
                  className="bg-primary hover:bg-coral-dark text-primary-foreground px-6 py-2 rounded-lg whitespace-nowrap font-medium transition-colors"
                >
                  Inscrever
                </button>
              </form>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-12">
          {/* Logo + descrição + social */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center mb-4">
              <span className="text-xl">
                <span className="font-normal text-white/90">Mercado</span>
                <span className="font-bold text-white">Franquia</span>
              </span>
            </Link>
            <p className="text-sm text-white/60 mb-6">
              O maior portal de ranking de franquias do Brasil. Compare, avalie
              e encontre a franquia ideal.
            </p>
            <div className="flex items-center gap-3">
              <a
                href="https://facebook.com"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
                aria-label="Facebook"
              >
                <FacebookIcon
                  width={18}
                  height={18}
                  color="rgba(255, 255, 255, 0.7)"
                />
              </a>
              <a
                href="https://instagram.com"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
                aria-label="Instagram"
              >
                <InstagramIcon
                  width={18}
                  height={18}
                  color="rgba(255, 255, 255, 0.7)"
                />
              </a>
              <a
                href="https://linkedin.com"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
                aria-label="LinkedIn"
              >
                <LinkedinIcon
                  width={18}
                  height={18}
                  color="rgba(255, 255, 255, 0.7)"
                />
              </a>
              <a
                href="https://youtube.com"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
                aria-label="YouTube"
              >
                <YoutubeIcon
                  width={18}
                  height={18}
                  color="rgba(255, 255, 255, 0.7)"
                />
              </a>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-white mb-4">Franquias</h4>
            <ul className="space-y-3">
              {footerLinks.franquias.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    className="text-sm text-white/60 hover:text-white transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-white mb-4">Suporte</h4>
            <ul className="space-y-3">
              {footerLinks.suporte.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    className="text-sm text-white/60 hover:text-white transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="border-t border-white/10 mt-12 pt-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-white/50">
              © 2026 Mercado Franquia. Todos os direitos reservados.
            </p>
            <p className="text-sm text-white/50">
              Desenvolvido por Mind Group.
            </p>
          </div>
        </div>
      </div>
    </footer>
  )
}
