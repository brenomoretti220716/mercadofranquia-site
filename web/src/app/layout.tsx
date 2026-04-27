import type { Metadata } from 'next'
import {
  Inter,
  Inter_Tight as InterTight,
  Instrument_Serif as InstrumentSerif,
  IBM_Plex_Sans as IBMPlexSans,
  IBM_Plex_Mono as IBMPlexMono,
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

// Fatia 1.8 — handoff editorial v10.
// Instrument Serif (substitui Fraunces — variable axes do Fraunces
// renderizavam glifos display dramaticos demais em tamanhos grandes;
// Instrument Serif tem desenho consistente em qualquer tamanho).
// Escopado via .landing no CSS module; nao afeta admin/editor.
const instrumentSerif = InstrumentSerif({
  subsets: ['latin'],
  weight: ['400'],
  style: ['normal', 'italic'],
  variable: '--font-instrument-serif',
  display: 'swap',
})

const ibmPlexSans = IBMPlexSans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-ibm-plex-sans',
  display: 'swap',
})

const ibmPlexMono = IBMPlexMono({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-ibm-plex-mono',
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
      className={`${inter.variable} ${plusJakartaSans.variable} ${interTight.variable} ${instrumentSerif.variable} ${ibmPlexSans.variable} ${ibmPlexMono.variable} ${jetbrainsMono.variable}`}
    >
      <body className={`${inter.className} antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
