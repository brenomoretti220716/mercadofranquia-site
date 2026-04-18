'use client'

import { useAuth, useLogout } from '@/src/hooks/users/useAuth'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'

type PrimaryItem = {
  key: string
  label: string
  href?: string
  icon: React.ReactNode
  matcher?: (p: string) => boolean
  isDrawer?: boolean
}

type DrawerItem = {
  label: string
  href: string
  disabled?: boolean
}

const DRAWER_ITEMS: DrawerItem[] = [
  { label: 'Segmentos ABF', href: '/admin/segmentos-abf' },
  { label: 'Avaliações', href: '#', disabled: true },
  { label: 'Patrocinados', href: '/admin/patrocinados' },
  { label: 'Big Numbers', href: '/admin/big-numbers' },
  { label: 'Administradores', href: '/admin/administradores' },
  { label: 'Franqueadores', href: '/admin/franqueadores' },
  { label: 'Configurações', href: '#', disabled: true },
]

function IconDashboard() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
    </svg>
  )
}

function IconFranquias() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 21h18" />
      <path d="M5 21V7l8-4v18" />
      <path d="M19 21V11l-6-4" />
    </svg>
  )
}

function IconUsers() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

function IconNoticias() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9h4" />
      <path d="M18 14h-8" />
      <path d="M15 18h-5" />
      <path d="M10 6h8v4h-8V6Z" />
    </svg>
  )
}

function IconMais() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="5" cy="12" r="1.5" />
      <circle cx="12" cy="12" r="1.5" />
      <circle cx="19" cy="12" r="1.5" />
    </svg>
  )
}

const PRIMARY: PrimaryItem[] = [
  {
    key: 'dashboard',
    label: 'Dashboard',
    href: '/admin',
    icon: <IconDashboard />,
    matcher: (p) => p === '/admin',
  },
  {
    key: 'franquias',
    label: 'Franquias',
    href: '/admin/franquias',
    icon: <IconFranquias />,
    matcher: (p) => p.startsWith('/admin/franquias'),
  },
  {
    key: 'usuarios',
    label: 'Usuários',
    href: '/admin/franqueados',
    icon: <IconUsers />,
    matcher: (p) =>
      p.startsWith('/admin/franqueados') ||
      p.startsWith('/admin/franqueadores') ||
      p.startsWith('/admin/administradores'),
  },
  {
    key: 'noticias',
    label: 'Notícias',
    href: '/admin/noticias',
    icon: <IconNoticias />,
    matcher: (p) => p.startsWith('/admin/noticias'),
  },
  {
    key: 'mais',
    label: 'Mais',
    icon: <IconMais />,
    isDrawer: true,
  },
]

export default function AdminBottomNav() {
  const pathname = usePathname()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { payload } = useAuth()
  const { handleLogout, isLoggingOut } = useLogout()

  useEffect(() => {
    if (drawerOpen) document.body.style.overflow = 'hidden'
    else document.body.style.overflow = ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [drawerOpen])

  useEffect(() => {
    setDrawerOpen(false)
  }, [pathname])

  return (
    <>
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white"
        style={{ borderTop: '0.5px solid #e5e5e5' }}
      >
        <div className="flex items-stretch h-14">
          {PRIMARY.map((item) => {
            const isActive = item.isDrawer
              ? drawerOpen
              : (item.matcher?.(pathname) ?? false)

            const color = isActive ? '#E25E3E' : '#666'
            const inner = (
              <>
                <span style={{ color }}>{item.icon}</span>
                <span
                  className="mt-0.5"
                  style={{
                    color,
                    fontSize: '10px',
                    letterSpacing: '0.2px',
                    fontWeight: isActive ? 600 : 500,
                  }}
                >
                  {item.label}
                </span>
              </>
            )

            if (item.isDrawer) {
              return (
                <button
                  key={item.key}
                  onClick={() => setDrawerOpen((v) => !v)}
                  aria-label={item.label}
                  aria-expanded={drawerOpen}
                  className="flex-1 flex flex-col items-center justify-center"
                >
                  {inner}
                </button>
              )
            }

            return (
              <Link
                key={item.key}
                href={item.href!}
                className="flex-1 flex flex-col items-center justify-center"
              >
                {inner}
              </Link>
            )
          })}
        </div>
      </nav>

      {drawerOpen && (
        <>
          <div
            className="md:hidden fixed inset-0 z-40 bg-black/40"
            onClick={() => setDrawerOpen(false)}
            aria-hidden="true"
          />
          <div
            className="md:hidden fixed left-0 right-0 bottom-14 z-50 bg-white rounded-t-2xl overflow-hidden"
            style={{ maxHeight: 'calc(100vh - 8rem)' }}
            role="dialog"
            aria-label="Mais itens"
          >
            <div
              className="px-5 py-3 flex items-center"
              style={{ borderBottom: '0.5px solid #e5e5e5' }}
            >
              <p
                className="font-semibold uppercase"
                style={{
                  color: '#111',
                  fontSize: '11px',
                  letterSpacing: '1.2px',
                }}
              >
                Mais ações
              </p>
              <button
                onClick={() => setDrawerOpen(false)}
                className="ml-auto text-[13px] text-[#666]"
              >
                Fechar
              </button>
            </div>
            <div className="overflow-y-auto" style={{ maxHeight: '60vh' }}>
              <ul>
                {DRAWER_ITEMS.map((item) => {
                  if (item.disabled) {
                    return (
                      <li key={item.label}>
                        <div
                          className="px-5 py-3 flex items-center cursor-not-allowed"
                          style={{
                            color: '#aaa',
                            borderBottom: '0.5px solid #f0f0f0',
                          }}
                        >
                          <span className="text-[14px]">{item.label}</span>
                          <span
                            className="ml-auto uppercase font-semibold rounded px-1.5 py-0.5"
                            style={{
                              background: '#f0f0f0',
                              color: '#888',
                              fontSize: '9px',
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
                        className="px-5 py-3 flex items-center text-[#111] hover:bg-[#f7f7f5] transition-colors"
                        style={{ borderBottom: '0.5px solid #f0f0f0' }}
                      >
                        <span className="text-[14px]">{item.label}</span>
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </div>
            <div
              className="px-5 py-3 flex items-center justify-between"
              style={{ borderTop: '0.5px solid #e5e5e5' }}
            >
              <div className="flex flex-col min-w-0">
                <span className="text-[12px] font-medium text-[#111] truncate">
                  {payload?.name ?? 'Admin'}
                </span>
                <span className="text-[10px] text-[#999] truncate">
                  Administrador
                </span>
              </div>
              <button
                onClick={handleLogout}
                disabled={isLoggingOut}
                className="text-[13px] font-medium disabled:opacity-50"
                style={{ color: '#E25E3E' }}
              >
                Sair
              </button>
            </div>
          </div>
        </>
      )}
    </>
  )
}
