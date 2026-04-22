interface Step {
  number: string
  title: string
  description: string
}

const steps: Step[] = [
  {
    number: '1',
    title: 'Cadastre sua marca',
    description:
      'Preencha seus dados e informações da franquia em 3 passos rápidos.',
  },
  {
    number: '2',
    title: 'Validamos sua marca',
    description: 'Nossa equipe revisa os dados em até 48h e aprova sua página.',
  },
  {
    number: '3',
    title: 'Apareça no portal',
    description:
      'Sua marca fica visível pra todos os investidores e começa a receber leads.',
  },
]

export default function LandingHowItWorks() {
  return (
    <section className="bg-gray-50">
      <div className="container mx-auto px-4 py-20 md:py-24">
        <div className="max-w-3xl mx-auto text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            Como anunciar sua franquia
          </h2>
        </div>

        <div className="relative max-w-5xl mx-auto">
          {/* Linha conectora (desktop only) */}
          <div
            className="hidden md:block absolute top-8 left-[16.66%] right-[16.66%] h-0.5 bg-gray-200"
            aria-hidden="true"
          />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-10 md:gap-8 relative">
            {steps.map((step) => (
              <div
                key={step.number}
                className="flex flex-col items-center text-center"
              >
                <div
                  className="relative z-10 w-16 h-16 rounded-full bg-[#E25E3E] text-white flex items-center justify-center text-2xl font-bold mb-5 shadow-lg"
                  aria-hidden="true"
                >
                  {step.number}
                </div>
                <h3 className="text-lg md:text-xl font-semibold text-gray-900 mb-3">
                  {step.title}
                </h3>
                <p className="text-sm md:text-base text-gray-600 leading-relaxed max-w-xs">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
