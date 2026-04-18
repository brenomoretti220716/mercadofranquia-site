'use client'

import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'

const TITLES: Array<{ match: (p: string) => boolean; title: string }> = [
  { match: (p) => p === '/admin', title: 'Dashboard' },
  {
    match: (p) => /^\/admin\/franquias\/[^/]+/.test(p),
    title: 'Detalhes da franquia',
  },
  { match: (p) => p.startsWith('/admin/franquias'), title: 'Franquias' },
  {
    match: (p) => p.startsWith('/admin/administradores'),
    title: 'Administradores',
  },
  {
    match: (p) => p.startsWith('/admin/franqueadores'),
    title: 'Franqueadores',
  },
  { match: (p) => p.startsWith('/admin/franqueados'), title: 'Franqueados' },
  { match: (p) => p.startsWith('/admin/noticias'), title: 'Notícias' },
  { match: (p) => p.startsWith('/admin/patrocinados'), title: 'Patrocinados' },
  {
    match: (p) => p.startsWith('/admin/segmentos-abf'),
    title: 'Segmentos ABF',
  },
  { match: (p) => p.startsWith('/admin/big-numbers'), title: 'Big Numbers' },
]

function resolveTitle(pathname: string): string {
  for (const entry of TITLES) {
    if (entry.match(pathname)) return entry.title
  }
  return 'Admin'
}

function formatDate(d: Date): string {
  return d
    .toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
    .replace('.', '')
}

export default function AdminTopbar() {
  const pathname = usePathname()
  const title = resolveTitle(pathname)
  const [today, setToday] = useState<string>('')

  useEffect(() => {
    setToday(formatDate(new Date()))
  }, [])

  return (
    <header
      className="hidden md:flex sticky top-16 z-30 bg-white h-11 items-center px-4 md:px-6"
      style={{ borderBottom: '0.5px solid #e5e5e5' }}
    >
      <h1
        className="text-[#111] font-medium truncate"
        style={{ fontSize: '13px' }}
      >
        {title}
      </h1>
      <div className="ml-auto flex items-center">
        <span
          className="font-mono uppercase"
          style={{
            color: '#999',
            fontSize: '11px',
            letterSpacing: '0.5px',
            visibility: today ? 'visible' : 'hidden',
          }}
        >
          {today || '00 xxx 0000'}
        </span>
      </div>
    </header>
  )
}
