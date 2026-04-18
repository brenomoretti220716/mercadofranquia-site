import dynamic from 'next/dynamic'
import { Suspense } from 'react'
import AdminNewsTableSkeleton from '@/src/components/ui/skeletons/AdminNewsTableSkeleton'

const AdminFontesPanel = dynamic(
  () => import('@/src/components/admin/panels/fontes/AdminFontesPanel'),
  {
    loading: () => <AdminNewsTableSkeleton />,
    ssr: true,
  },
)

export default function AdminFontesPage() {
  return (
    <Suspense fallback={<AdminNewsTableSkeleton />}>
      <AdminFontesPanel />
    </Suspense>
  )
}
