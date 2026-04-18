'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const ITEMS = [
  { label: 'Home', href: '/' },
  { label: 'Quiz', href: '/quiz' },
  { label: 'Ranking', href: '/ranking' },
  { label: 'Mercado', href: '/mercado' },
  { label: 'Notícias', href: '/noticias' },
]

export default function MobileQuickNav() {
  const pathname = usePathname()

  return (
    <nav
      className="md:hidden bg-white"
      style={{ borderBottom: '0.5px solid #e5e5e5' }}
    >
      <div className="flex overflow-x-auto scrollbar-hide">
        {ITEMS.map((item) => {
          const isActive =
            item.href === pathname ||
            (item.href === '/mercado' && pathname === '/mercado')

          return (
            <Link
              key={item.label}
              href={item.href}
              className={`shrink-0 whitespace-nowrap text-[13px] px-3.5 py-2.5 transition-colors ${
                isActive
                  ? 'text-[#111] border-b-2 border-[#E25E3E]'
                  : 'text-[#444] border-b-2 border-transparent'
              }`}
            >
              {item.label}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
