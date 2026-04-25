'use client'

import { useState } from 'react'
import MyFranchisesList from '@/src/components/franqueadores/panels/franchises/MyFranchisesList'
import CreateAdditionalFranchiseForm from '@/src/components/franqueadores/panels/franchises/CreateAdditionalFranchiseForm'
import ClaimCard from '@/src/components/franqueadores/panels/franchises/ClaimCard'
import { useMyFranchisorRequest } from '@/src/hooks/users/useFranchisorRequest'
import { FranchisorRequestStatus } from '@/src/schemas/users/FranchisorRequest'

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
  const { data: myRequest } = useMyFranchisorRequest()

  const showClaim =
    myRequest?.mode === 'EXISTING' &&
    (myRequest.status === FranchisorRequestStatus.PENDING ||
      myRequest.status === FranchisorRequestStatus.UNDER_REVIEW)

  return (
    <>
      <MyFranchisesList onCreateNew={() => setIsCreateOpen(true)} />
      {showClaim && myRequest && (
        <section className="m-4 sm:m-6 md:m-10">
          <h2 className="text-xl font-semibold text-foreground mb-4">
            Reivindicações em análise
          </h2>
          <ClaimCard request={myRequest} />
        </section>
      )}
      <CreateAdditionalFranchiseForm
        open={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      />
    </>
  )
}
