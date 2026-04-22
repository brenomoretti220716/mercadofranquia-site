import Link from 'next/link'

/**
 * Hero da landing /anuncie-sua-franquia.
 * Fundo preto `#111111`, duas CTAs (primária laranja, secundária outline).
 */
export default function LandingHero() {
  return (
    <section className="bg-[#111111] text-white">
      <div className="container mx-auto px-4 py-20 md:py-28">
        <div className="max-w-3xl">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight mb-6">
            Anuncie sua franquia no maior portal de franquias do Brasil
          </h1>
          <p className="text-lg md:text-xl text-white/70 mb-10 max-w-2xl">
            Receba leads qualificados de investidores interessados em abrir
            unidades da sua marca.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <Link
              href="/anuncie-sua-franquia/cadastro"
              className="inline-flex items-center justify-center px-8 py-4 rounded-full bg-[#E25E3E] hover:bg-[#c04e2e] text-white font-semibold text-base transition-colors"
            >
              Cadastrar minha marca
            </Link>
            <Link
              href="#contato"
              className="inline-flex items-center justify-center px-8 py-4 rounded-full border-2 border-white/30 hover:border-white hover:bg-white/5 text-white font-semibold text-base transition-colors"
            >
              Falar com time comercial
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
