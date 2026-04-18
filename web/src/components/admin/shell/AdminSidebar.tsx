'use client'

import { useAuth, useLogout } from '@/src/hooks/users/useAuth'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

type NavItem = {
  label: string
  href: string
  counter?: string
  disabled?: boolean
  matcher?: (pathname: string) => boolean
}

type NavSection = {
  title: string
  items: NavItem[]
}

const SECTIONS: NavSection[] = [
  {
    title: 'Principal',
    items: [
      {
        label: 'Dashboard',
        href: '/admin',
        matcher: (p) => p === '/admin',
      },
      {
        label: 'Franquias',
        href: '/admin/franquias',
        counter: '1.409',
        matcher: (p) => p.startsWith('/admin/franquias'),
      },
      {
        label: 'Usuários',
        href: '/admin/franqueados',
        // shortcut — specific Sistema items take precedence
        matcher: () => false,
      },
      {
        label: 'Notícias',
        href: '/admin/noticias',
        matcher: (p) => p.startsWith('/admin/noticias'),
      },
    ],
  },
  {
    title: 'Dados',
    items: [
      {
        label: 'Segmentos ABF',
        href: '/admin/segmentos-abf',
        matcher: (p) => p.startsWith('/admin/segmentos-abf'),
      },
      {
        label: 'Avaliações',
        href: '#',
        disabled: true,
      },
      {
        label: 'Patrocinados',
        href: '/admin/patrocinados',
        matcher: (p) => p.startsWith('/admin/patrocinados'),
      },
      {
        label: 'Big Numbers',
        href: '/admin/big-numbers',
        matcher: (p) => p.startsWith('/admin/big-numbers'),
      },
    ],
  },
  {
    title: 'Sistema',
    items: [
      {
        label: 'Administradores',
        href: '/admin/administradores',
        matcher: (p) => p.startsWith('/admin/administradores'),
      },
      {
        label: 'Franqueadores',
        href: '/admin/franqueadores',
        matcher: (p) => p.startsWith('/admin/franqueadores'),
      },
      {
        label: 'Franqueados',
        href: '/admin/franqueados',
        matcher: (p) => p.startsWith('/admin/franqueados'),
      },
      {
        label: 'Configurações',
        href: '#',
        disabled: true,
      },
    ],
  },
]

function getInitials(name: string | undefined | null): string {
  if (!name) return 'A'
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

function roleLabel(role: string | undefined | null): string {
  switch (role) {
    case 'ADMIN':
      return 'Administrador'
    case 'FRANCHISOR':
      return 'Franqueador'
    case 'FRANCHISEE':
      return 'Franqueado'
    case 'CANDIDATE':
      return 'Candidato'
    case 'ENTHUSIAST':
      return 'Entusiasta'
    case 'MEMBER':
      return 'Membro'
    default:
      return '—'
  }
}

export default function AdminSidebar() {
  const pathname = usePathname()
  const { payload } = useAuth()
  const { handleLogout, isLoggingOut } = useLogout()

  return (
    <aside className="hidden md:flex fixed left-0 top-16 h-[calc(100vh-4rem)] w-[220px] bg-[#111] flex-col z-40">
      <div className="px-5 h-14 flex items-center gap-2 border-b border-[#1e1e1e]">
        <span className="text-white font-display font-semibold text-[15px] tracking-tight">
          MercadoFranquia
        </span>
        <span
          className="ml-auto text-white font-semibold uppercase rounded px-1.5 py-0.5"
          style={{
            background: '#C73E1D',
            fontSize: '9px',
            letterSpacing: '0.8px',
          }}
        >
          Admin
        </span>
      </div>

      <nav className="flex-1 overflow-y-auto py-4">
        {SECTIONS.map((section) => (
          <div key={section.title} className="mb-5">
            <p
              className="px-5 mb-2 font-semibold uppercase"
              style={{
                color: '#666',
                fontSize: '10px',
                letterSpacing: '1.2px',
              }}
            >
              {section.title}
            </p>
            <ul>
              {section.items.map((item) => {
                const isActive =
                  !item.disabled &&
                  (item.matcher
                    ? item.matcher(pathname)
                    : pathname === item.href)

                if (item.disabled) {
                  return (
                    <li key={item.label}>
                      <div
                        className="mx-2 px-3 py-2 rounded-md flex items-center gap-2 cursor-not-allowed"
                        style={{ color: '#555' }}
                      >
                        <span className="text-[13px]">{item.label}</span>
                        <span
                          className="ml-auto uppercase font-semibold rounded px-1.5 py-0.5"
                          style={{
                            background: '#1e1e1e',
                            color: '#777',
                            fontSize: '8px',
                            letterSpacing: '0.6px',
                          }}
                        >
                          Em breve
                        </span>
                      </div>
                    </li>
                  )
                }

                return (
                  <li key={item.label}>
                    <Link
                      href={item.href}
                      className={`mx-2 px-3 py-2 rounded-md flex items-center gap-2 transition-colors text-[13px] ${
                        isActive
                          ? 'bg-[#1e1e1e] text-white'
                          : 'text-[#888] hover:bg-[#1a1a1a] hover:text-white'
                      }`}
                    >
                      {isActive && (
                        <span
                          className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                          style={{ background: '#E25E3E' }}
                          aria-hidden="true"
                        />
                      )}
                      <span className={isActive ? '' : 'ml-[14px]'}>
                        {item.label}
                      </span>
                      {item.counter && (
                        <span
                          className="ml-auto font-mono"
                          style={{ color: '#555', fontSize: '11px' }}
                        >
                          {item.counter}
                        </span>
                      )}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-[#1e1e1e] p-3">
        <div className="flex items-center gap-3 px-2 py-2">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 font-semibold text-[12px]"
            style={{ background: '#1e1e1e', color: '#E25E3E' }}
          >
            {getInitials(payload?.name)}
          </div>
          <div className="flex flex-col min-w-0 flex-1">
            <span className="text-white text-[12px] font-medium truncate">
              {payload?.name ?? 'Admin'}
            </span>
            <span className="text-[#666] text-[10px] truncate">
              {roleLabel(payload?.role)}
            </span>
          </div>
        </div>
        <button
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="w-full mt-1 px-3 py-2 rounded-md text-left text-[12px] font-medium transition-colors hover:bg-[#1a1a1a] disabled:opacity-50"
          style={{ color: '#E25E3E' }}
        >
          Sair
        </button>
      </div>
    </aside>
  )
}
