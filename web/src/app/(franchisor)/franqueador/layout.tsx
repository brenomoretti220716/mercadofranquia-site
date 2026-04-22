'use client'

import Header from '@/src/components/layout/Header'
import FooterMinimal from '@/src/components/shared/FooterMinimal'

export default function FranchisorLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <div className="flex-1">{children}</div>
      <FooterMinimal />
    </div>
  )
}
