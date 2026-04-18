'use client'

import AdminDashboardPanel from '@/src/components/admin/panels/dashboard/AdminDashboardPanel'
import { isAdmin, useAuth } from '@/src/hooks/users/useAuth'
import { Suspense } from 'react'

function DashboardSkeleton() {
  return (
    <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 md:py-8 space-y-8 animate-pulse">
      <div>
        <div className="h-3 w-24 bg-[#e5e5e5] rounded mb-2" />
        <div className="h-7 w-64 bg-[#e5e5e5] rounded" />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="bg-white rounded-xl border border-[#e5e5e5] p-5 h-28"
          />
        ))}
      </div>
      <div className="bg-white rounded-xl border border-[#e5e5e5] h-64" />
    </div>
  )
}

export default function AdminContent() {
  const { isValidating, payload } = useAuth()

  if (isValidating) {
    return <DashboardSkeleton />
  }

  if (!isAdmin(payload)) {
    return null
  }

  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <AdminDashboardPanel />
    </Suspense>
  )
}
