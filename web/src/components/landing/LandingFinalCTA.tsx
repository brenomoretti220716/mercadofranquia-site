import Link from 'next/link'

/**
 * CTA final da landing — fundo laranja-vermelho, botão preto grande.
 */
export default function LandingFinalCTA() {
  return (
    <section className="bg-[#E25E3E] text-white">
      <div className="container mx-auto px-4 py-20 md:py-24">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl md:text-5xl font-bold mb-5 leading-tight">
            Pronto pra começar?
          </h2>
          <p className="text-lg md:text-xl text-white/90 mb-10">
            Cadastre sua marca em poucos minutos e comece a receber leads
            qualificados.
          </p>
          <Link
            href="/anuncie-sua-franquia/cadastro"
            className="inline-flex items-center justify-center px-8 py-4 md:px-10 md:py-5 rounded-full bg-[#111111] hover:bg-black text-white font-semibold text-base md:text-lg transition-colors"
          >
            Cadastrar minha marca grátis
          </Link>
        </div>
      </div>
    </section>
  )
}
