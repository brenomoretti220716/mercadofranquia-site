'use client'

import type { Franchise } from '@/src/schemas/franchises/Franchise'
import BusinessModelsSection from '@/src/components/franqueadores/panels/franchises/businessModels/BusinessModelsSection'

interface BusinessModelsTabProps {
  franchise: Franchise
  token: string
}

export default function BusinessModelsTab({
  franchise,
  token,
}: BusinessModelsTabProps) {
  return (
    <BusinessModelsSection
      franchiseId={franchise.id}
      token={token}
      isOwner={true}
    />
  )
}
