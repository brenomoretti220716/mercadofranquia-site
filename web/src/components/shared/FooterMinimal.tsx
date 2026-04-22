import Link from 'next/link'

export default function FooterMinimal() {
  return (
    <footer className="bg-[#111111] text-white/70 border-t border-white/10">
      <div className="container mx-auto px-4 h-12 flex items-center justify-center text-xs md:text-sm">
        <span>© 2026 Mercado Franquia</span>
        <span className="mx-2 text-white/30">·</span>
        <a
          href="mailto:suporte@mercadofranquia.com.br"
          className="hover:text-white transition-colors"
        >
          Suporte
        </a>
        <span className="mx-2 text-white/30">·</span>
        <Link href="/termos" className="hover:text-white transition-colors">
          Termos de uso
        </Link>
      </div>
    </footer>
  )
}
