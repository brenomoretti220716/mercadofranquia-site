import type { Metadata } from 'next'
import {
  Inter,
  Inter_Tight as InterTight,
  Fraunces,
  JetBrains_Mono as JetBrainsMono,
  Plus_Jakarta_Sans as PlusJakartaSans,
} from 'next/font/google'
import '../globals.css'
import { Providers } from './providers'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

const plusJakartaSans = PlusJakartaSans({
  subsets: ['latin'],
  variable: '--font-plus-jakarta-sans',
  display: 'swap',
})

// Design system v9 (landing publica do redesign — Fatia 2 em diante).
const interTight = InterTight({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-inter-tight',
  display: 'swap',
})

const fraunces = Fraunces({
  subsets: ['latin'],
  weight: ['400'],
  style: ['italic'],
  variable: '--font-fraunces',
  display: 'swap',
})

const jetbrainsMono = JetBrainsMono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-jetbrains-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  title: {
    default: 'Mercado Franquias',
    template: '%s | Mercado Franquias',
  },
  description:
    'O maior portal de ranking de franquias do Brasil. Compare, avalie e encontre a franquia ideal.',
  metadataBase:
    typeof process.env.NEXT_PUBLIC_SITE_URL === 'string'
      ? new URL(process.env.NEXT_PUBLIC_SITE_URL)
      : undefined,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="pt-br"
      className={`${inter.variable} ${plusJakartaSans.variable} ${interTight.variable} ${fraunces.variable} ${jetbrainsMono.variable}`}
    >
      <body className={`${inter.className} antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
