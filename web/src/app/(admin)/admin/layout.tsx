'use client'

import AdminSidebar from '@/src/components/admin/shell/AdminSidebar'
import AdminTopbar from '@/src/components/admin/shell/AdminTopbar'
import Header from '@/src/components/layout/Header'
import FooterMinimal from '@/src/components/shared/FooterMinimal'

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div
      className="min-h-screen"
      style={{ background: 'var(--color-background-tertiary)' }}
    >
      <Header />
      <AdminSidebar />
      <div className="md:pl-[220px] flex flex-col min-h-[calc(100vh-4rem)]">
        <AdminTopbar />
        <main className="flex-1">{children}</main>
        <FooterMinimal />
      </div>
    </div>
  )
}
