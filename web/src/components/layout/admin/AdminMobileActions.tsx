'use client'

import { removeClientAuthCookie } from '@/src/utils/clientCookie'
import Link from 'next/link'
import { useState } from 'react'
import { toast } from 'sonner'

interface AdminMobileActionsProps {
  handleMobileMenuClose: () => void
}

export const AdminMobileActions = ({
  handleMobileMenuClose,
}: AdminMobileActionsProps) => {
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  const handleLogout = async () => {
    try {
      setIsLoggingOut(true)
      removeClientAuthCookie()
      toast.success('Logout realizado com sucesso!')
      setTimeout(() => {
        window.location.href = '/'
      }, 1500)
    } catch (error) {
      console.error('Erro ao fazer logout: ', error)
      toast.error('Erro ao fazer o Logout')
    }
  }

  return (
    <div className="p-6 space-y-1" style={{ borderTop: '1px solid #222' }}>
      <Link
        href="/"
        className="block w-full text-left p-3 rounded-lg transition-colors text-white hover:text-[#E25E3E] cursor-pointer"
        onClick={handleMobileMenuClose}
      >
        Painel de Início
      </Link>
      <Link
        href="/favoritos"
        className="block w-full text-left p-3 rounded-lg transition-colors text-white hover:text-[#E25E3E] cursor-pointer"
        onClick={handleMobileMenuClose}
      >
        Favoritos
      </Link>
      <button
        onClick={() => {
          handleLogout()
          handleMobileMenuClose()
        }}
        disabled={isLoggingOut}
        className="w-full text-left p-3 rounded-lg transition-colors text-[#E25E3E] cursor-pointer"
      >
        Sair
      </button>
    </div>
  )
}
