import Header from '@/src/components/layout/Header'
import Footer from '@/src/components/shared/Footer'

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div>
      <Header variant="public" />
      {children}
      <Footer />
    </div>
  )
}
