'use client'

import UserLogin from '@/src/components/autenticacao/UserLogin'
import ModalLogin from '@/src/components/autenticacao/ModalLogin'

export default function LoginPage() {
  return (
    <div className="flex flex-col min-h-screen">
      <div className="flex flex-1 flex-col justify-center items-center px-4 py-8">
        <div className="w-full max-w-md">
          <ModalLogin
            tittleText="Bem-vindo de volta!"
            subtittleText="Faça login para continuar e ter acesso a conteúdos exclusivos."
          >
            <UserLogin />
          </ModalLogin>
        </div>
      </div>
    </div>
  )
}
