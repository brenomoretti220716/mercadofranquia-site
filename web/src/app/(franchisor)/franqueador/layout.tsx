'use client'

import Header from '@/src/components/header/Header'

export default function FranchisorLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div>
      <Header />
      {children}
    </div>
  )
}
