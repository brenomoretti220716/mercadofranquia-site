import { Eye, Users, LayoutDashboard, Gift } from 'lucide-react'

interface Benefit {
  icon: React.ComponentType<{ className?: string }>
  title: string
  description: string
}

const benefits: Benefit[] = [
  {
    icon: Eye,
    title: 'Visibilidade nacional',
    description:
      'Sua marca vista por milhares de investidores qualificados todos os meses.',
  },
  {
    icon: Users,
    title: 'Leads qualificados',
    description:
      'Receba contatos de investidores realmente interessados, filtrados por região e perfil.',
  },
  {
    icon: LayoutDashboard,
    title: 'Painel dedicado',
    description:
      'Dashboard pra gerenciar sua página, ver leads e atualizar informações da marca.',
  },
  {
    icon: Gift,
    title: 'Grátis pra começar',
    description:
      'Anuncie sua marca sem custo inicial. Planos pagos para destaque premium.',
  },
]

export default function LandingBenefits() {
  return (
    <section className="bg-white">
      <div className="container mx-auto px-4 py-20 md:py-24">
        <div className="max-w-3xl mx-auto text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            Por que anunciar no Mercado Franquia?
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 max-w-5xl mx-auto">
          {benefits.map((b) => {
            const Icon = b.icon
            return (
              <div
                key={b.title}
                className="flex gap-5 p-6 md:p-7 rounded-2xl border border-gray-200 hover:border-[#E25E3E]/30 hover:shadow-sm transition-all"
              >
                <div
                  className="w-12 h-12 rounded-xl bg-[#FFF4F0] flex items-center justify-center shrink-0"
                  aria-hidden="true"
                >
                  <Icon className="w-6 h-6 text-[#E25E3E]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {b.title}
                  </h3>
                  <p className="text-sm md:text-base text-gray-600 leading-relaxed">
                    {b.description}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
