import type { Metadata } from 'next'
import LandingHero from '@/src/components/landing/LandingHero'
import LandingBenefits from '@/src/components/landing/LandingBenefits'
import LandingHowItWorks from '@/src/components/landing/LandingHowItWorks'
import LandingFinalCTA from '@/src/components/landing/LandingFinalCTA'

export const metadata: Metadata = {
  title: 'Anuncie sua franquia grátis — Mercado Franquia',
  description:
    'Cadastre sua marca no maior portal de franquias do Brasil e receba leads qualificados de investidores interessados em abrir unidades da sua franquia.',
  openGraph: {
    title: 'Anuncie sua franquia grátis — Mercado Franquia',
    description:
      'Cadastre sua marca no maior portal de franquias do Brasil e receba leads qualificados de investidores.',
    type: 'website',
  },
}

export default function AnuncieSuaFranquiaPage() {
  return (
    <main>
      <LandingHero />
      <LandingBenefits />
      <LandingHowItWorks />
      <section id="contato" className="bg-[#111111] text-white">
        <div className="container mx-auto px-4 py-20 md:py-24">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-5">Dúvidas?</h2>
            <p className="text-lg md:text-xl text-white/80">
              Fale com nosso time comercial pelo email{' '}
              <a
                href="mailto:contato@mercadofranquia.com.br"
                className="text-[#E25E3E] hover:underline"
              >
                contato@mercadofranquia.com.br
              </a>
            </p>
          </div>
        </div>
      </section>
      <LandingFinalCTA />
    </main>
  )
}
