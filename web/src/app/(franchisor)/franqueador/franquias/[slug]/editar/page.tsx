'use client'

import { useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { franchiseQueries } from '@/src/queries/franchises'
import { useAuth } from '@/src/hooks/users/useAuth'
import FranchiseEditor from '@/src/components/franchise-editor/FranchiseEditor'

export default function EditarFranquiaPage() {
  const params = useParams<{ slug: string }>()
  const slug = params?.slug
  const router = useRouter()
  const { token, payload, isAuthenticated, isValidating } = useAuth()

  const {
    data: franchise,
    isLoading,
    isError,
  } = useQuery({
    ...franchiseQueries.detail(slug ?? '', token ?? undefined),
    enabled: !!slug && !!token && isAuthenticated,
  })

  useEffect(() => {
    if (!isValidating && !isAuthenticated) {
      router.replace('/autenticacao/entrar')
    }
  }, [isValidating, isAuthenticated, router])

  useEffect(() => {
    if (!franchise || !payload) return
    const isOwner = franchise.ownerId === payload.id
    const isAdmin = payload.role === 'ADMIN'
    if (!isOwner && !isAdmin) {
      toast.error('Você não tem acesso a essa franquia.')
      router.replace('/franqueador/minhas-franquias')
    }
  }, [franchise, payload, router])

  if (isValidating || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-muted-foreground">Carregando franquia...</p>
      </div>
    )
  }

  if (isError || !franchise) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
        <h1 className="text-xl font-semibold text-foreground mb-2">
          Franquia não encontrada
        </h1>
        <p className="text-muted-foreground text-sm max-w-md">
          Verifique o link ou volte pro painel principal.
        </p>
      </div>
    )
  }

  if (!token || !payload) return null

  const isOwner = franchise.ownerId === payload.id
  const isAdmin = payload.role === 'ADMIN'
  if (!isOwner && !isAdmin) return null

  return (
    <FranchiseEditor
      franchise={franchise}
      token={token}
      userRole={payload.role}
    />
  )
}
