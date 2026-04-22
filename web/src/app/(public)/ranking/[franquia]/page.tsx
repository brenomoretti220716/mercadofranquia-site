'use client'

import SelectedFranchise from '@/src/components/franchisees/franchises/panel/SelectedFranchise'
import AdminSelectedFranchiseSkeleton from '@/src/components/ui/skeletons/AdminSelectedFranchiseSkeleton'
import { Suspense } from 'react'

export default function FranchisePage() {
  return (
    <>
      <Suspense fallback={<AdminSelectedFranchiseSkeleton />}>
        <SelectedFranchise />
      </Suspense>
    </>
  )
}
