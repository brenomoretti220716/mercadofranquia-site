'use client'

import { useState } from 'react'
import MyFranchisesList from '@/src/components/franchisors/panels/franchises/MyFranchisesList'
import CreateAdditionalFranchiseForm from '@/src/components/franchisors/panels/franchises/CreateAdditionalFranchiseForm'

/**
 * Página principal do painel do franqueador — lista de Franchises + criar nova.
 *
 * Substitui o componente legado FranchisorSelectedFranchise (quebrado desde
 * migração NestJS→FastAPI). Usa endpoints novos da Sprint 1:
 * - GET /franchisor/franchises/me (listar)
 * - POST /franchisor/franchises (criar marca adicional)
 */
export default function MyFranchisesPage() {
  const [isCreateOpen, setIsCreateOpen] = useState(false)

  return (
    <>
      <MyFranchisesList onCreateNew={() => setIsCreateOpen(true)} />
      <CreateAdditionalFranchiseForm
        open={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      />
    </>
  )
}
