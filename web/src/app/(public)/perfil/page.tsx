'use client'

import PerfilPageSkeleton from '@/src/components/ui/skeletons/PerfilPageSkeleton'
import dynamic from 'next/dynamic'

const PerfilPageClient = dynamic(
  () => import('@/src/components/pages/perfil/PerfilPageClient'),
  {
    ssr: false,
    loading: () => <PerfilPageSkeleton />,
  },
)

export default function PerfilPage() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <main className="container mx-auto flex-1 px-4 py-8 md:py-12">
        <PerfilPageClient />
      </main>
    </div>
  )
}
