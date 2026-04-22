import type { Metadata } from 'next'
import FranchisorRegisterFlow from '@/src/components/landing/FranchisorRegisterFlow'

export const metadata: Metadata = {
  title: 'Cadastre sua franquia — Mercado Franquia',
  description:
    'Crie sua conta como franqueador e cadastre sua marca no Mercado Franquia para receber leads qualificados de investidores.',
}

export default function CadastroFranchisorPage() {
  return (
    <div className="flex flex-col min-h-screen">
      <div className="flex flex-1 flex-col justify-center items-center px-4 py-8 sm:py-12">
        <div className="w-full max-w-xl">
          <div className="flex flex-col bg-white relative w-full h-auto rounded-2xl shadow-sm border border-border/50 p-4 sm:p-6 md:p-8">
            <FranchisorRegisterFlow />
          </div>
        </div>
      </div>
    </div>
  )
}
