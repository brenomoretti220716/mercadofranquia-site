'use client'

import Link from 'next/link'

const STEP_LABELS = [
  'Conexão',
  'Interesses',
  'Operacional',
  'Visão',
  'Investidor',
  'Financeiro',
  'Localização',
] as const

const AVATAR_COLORS = [
  '#E25E3E',
  '#F4A582',
  '#4C6A92',
  '#6B8E7F',
  '#A89080',
] as const

const QUIZ_HREF = '/login?redirect=/quiz'

export default function QuizIntro() {
  return (
    <>
      <section
        className="bg-[#0d0d0d]"
        style={{ borderBottom: '2px solid #E25E3E' }}
      >
        <div className="container mx-auto px-4 py-16 sm:py-20 md:py-24 max-w-4xl text-center">
          <p
            className="font-semibold uppercase mb-4 text-[#E25E3E]"
            style={{ fontSize: '10px', letterSpacing: '1.5px' }}
          >
            Quiz · Perfil de investidor
          </p>

          <h1
            className="font-display font-semibold text-white tracking-tight mb-5"
            style={{ fontSize: '28px', lineHeight: 1.15 }}
          >
            Qual franquia combina com você?
          </h1>

          <p
            className="mx-auto mb-10 max-w-xl leading-relaxed"
            style={{ color: '#666', fontSize: '14px' }}
          >
            Um questionário sobre seu perfil, capital e objetivos. Ao final, sua
            seleção personalizada de franquias entre milhares de redes
            cadastradas.
          </p>

          <div className="flex justify-center mb-10 overflow-x-auto px-1 -mx-1">
            <div className="flex items-center flex-shrink-0">
              {STEP_LABELS.map((label, idx) => {
                const isActive = idx === 0
                return (
                  <div key={label} className="flex items-center flex-shrink-0">
                    <div
                      className="flex items-center justify-center w-8 h-8 rounded-full font-mono text-[11px] font-semibold flex-shrink-0"
                      style={
                        isActive
                          ? { background: '#E25E3E', color: '#fff' }
                          : {
                              background: '#1e1e1e',
                              color: '#666',
                              border: '1px solid #333',
                            }
                      }
                      aria-current={isActive ? 'step' : undefined}
                      aria-label={`Passo ${idx + 1}: ${label}`}
                    >
                      {idx + 1}
                    </div>
                    {idx < STEP_LABELS.length - 1 && (
                      <div
                        className="flex-shrink-0"
                        style={{
                          width: '20px',
                          height: '1px',
                          background: '#333',
                        }}
                      />
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href={QUIZ_HREF}
              className="inline-flex items-center justify-center px-6 py-3 rounded-lg bg-[#E25E3E] text-white font-medium hover:bg-[#d04f30] transition-colors"
            >
              Começar quiz →
            </Link>
            <Link
              href={QUIZ_HREF}
              className="inline-flex items-center justify-center px-6 py-3 rounded-lg border border-white/25 text-white font-medium hover:bg-white/5 transition-colors"
            >
              Já tenho conta · Entrar
            </Link>
          </div>
        </div>
      </section>

      <section className="bg-white">
        <div className="container mx-auto px-4 py-12 sm:py-16 md:py-20 max-w-5xl">
          <div className="pt-4 mb-8" style={{ borderTop: '2px solid #111' }}>
            <p
              className="font-semibold uppercase text-[#111]"
              style={{ fontSize: '11px', letterSpacing: '1.5px' }}
            >
              O que você vai descobrir
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div className="border border-[#e5e5e5] rounded-xl p-6 bg-white">
              <div className="w-10 h-10 rounded-lg bg-[#E25E3E]/10 flex items-center justify-center mb-4">
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#E25E3E"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </div>
              <h3 className="text-base font-semibold text-[#111] mb-1.5">
                Seu perfil de investidor
              </h3>
              <p
                className="leading-relaxed"
                style={{ color: '#666', fontSize: '14px' }}
              >
                Identificamos seu estilo, tolerância a risco e como você prefere
                conduzir um negócio.
              </p>
            </div>

            <div className="border border-[#e5e5e5] rounded-xl p-6 bg-white">
              <div className="w-10 h-10 rounded-lg bg-[#E25E3E]/10 flex items-center justify-center mb-4">
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#E25E3E"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <h3 className="text-base font-semibold text-[#111] mb-1.5">
                Franquias compatíveis
              </h3>
              <p
                className="leading-relaxed"
                style={{ color: '#666', fontSize: '14px' }}
              >
                Uma seleção personalizada de redes com análise de fit, ranqueada
                pela compatibilidade com seu perfil.
              </p>
            </div>
          </div>

          <div className="border border-[#e5e5e5] rounded-xl p-6 sm:p-8 bg-white mb-10">
            <p
              className="font-semibold uppercase mb-5"
              style={{
                color: '#999',
                fontSize: '11px',
                letterSpacing: '1.5px',
              }}
            >
              As 7 etapas
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-0">
              {STEP_LABELS.map((label, idx) => (
                <div
                  key={label}
                  className="flex items-baseline gap-3 py-3 border-b border-[#f0f0f0]"
                >
                  <span
                    className="font-mono flex-shrink-0"
                    style={{ color: '#bbb', fontSize: '11px' }}
                  >
                    {String(idx + 1).padStart(2, '0')}
                  </span>
                  <span className="text-[#111] font-medium text-sm">
                    {label}
                  </span>
                  <span
                    className="ml-auto flex-shrink-0 font-mono"
                    style={{ color: '#999', fontSize: '11px' }}
                  >
                    ~1 min
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-4 justify-center text-center sm:text-left">
            <div className="flex -space-x-2 flex-shrink-0">
              {AVATAR_COLORS.map((color, i) => (
                <div
                  key={i}
                  className="w-8 h-8 rounded-full border-2 border-white"
                  style={{ background: color }}
                  aria-hidden="true"
                />
              ))}
            </div>
            <p style={{ color: '#666', fontSize: '14px' }}>
              <span className="font-semibold text-[#111]">
                2.400 investidores
              </span>{' '}
              já descobriram sua franquia ideal
            </p>
          </div>
        </div>
      </section>
    </>
  )
}
