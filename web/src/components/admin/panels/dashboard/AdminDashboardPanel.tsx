'use client'

import { useFranchises } from '@/src/hooks/franchises/useFranchises'
import { useAuth } from '@/src/hooks/users/useAuth'
import { newsQueries } from '@/src/queries/news'
import { userQueries } from '@/src/queries/users'
import type { Franchise } from '@/src/schemas/franchises/Franchise'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'

const formatNumber = (n: number) => n.toLocaleString('pt-BR')

const formatCurrency = (v: number | null | undefined): string => {
  if (v == null || v === 0) return '—'
  return v.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  })
}

const formatInvestmentRange = (
  min: number | null | undefined,
  max: number | null | undefined,
): string => {
  const hasMin = min != null && min > 0
  const hasMax = max != null && max > 0
  if (hasMin && hasMax && min !== max) {
    return `${formatCurrency(min)} – ${formatCurrency(max)}`
  }
  if (hasMin) return formatCurrency(min)
  if (hasMax) return formatCurrency(max)
  return '—'
}

function BloombergSectionHeader({
  title,
  extra,
}: {
  title: string
  extra?: React.ReactNode
}) {
  return (
    <div
      className="pt-4 mb-4 flex items-end justify-between"
      style={{ borderTop: '2px solid #111' }}
    >
      <p
        className="uppercase font-semibold text-[#111]"
        style={{ fontSize: '11px', letterSpacing: '1.5px' }}
      >
        {title}
      </p>
      {extra}
    </div>
  )
}

function StatsCard({
  label,
  value,
  hint,
  accent,
}: {
  label: string
  value: string
  hint?: string
  accent?: boolean
}) {
  return (
    <div className="bg-white rounded-xl border border-[#e5e5e5] p-5">
      <p
        className="uppercase font-semibold mb-2.5"
        style={{ color: '#666', fontSize: '10px', letterSpacing: '1.2px' }}
      >
        {label}
      </p>
      <p
        className="font-display font-semibold tracking-tight leading-none text-[28px]"
        style={{ color: accent ? '#E25E3E' : '#111' }}
      >
        {value}
      </p>
      {hint && (
        <p className="text-[11px] mt-2" style={{ color: '#999' }}>
          {hint}
        </p>
      )}
    </div>
  )
}

function StatusBadge({ isActive }: { isActive: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 ${
        isActive ? 'text-[#111]' : 'text-[#999]'
      }`}
    >
      <span
        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
        style={{ background: isActive ? '#22c55e' : '#d1d5db' }}
        aria-hidden="true"
      />
      <span className="text-[12px]">{isActive ? 'Ativa' : 'Inativa'}</span>
    </span>
  )
}

function RecentFranchisesTable({ franchises }: { franchises: Franchise[] }) {
  if (franchises.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-[#e5e5e5] p-6 text-center text-[13px] text-[#999]">
        Nenhuma franquia cadastrada ainda.
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-[#e5e5e5] overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px]">
          <thead>
            <tr>
              {['Nome', 'Segmento', 'Investimento', 'Status', ''].map(
                (h, i) => (
                  <th
                    key={i}
                    className="uppercase font-semibold text-left px-4 py-3"
                    style={{
                      color: '#666',
                      fontSize: '10px',
                      letterSpacing: '1.2px',
                      borderBottom: '0.5px solid #e5e5e5',
                    }}
                  >
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {franchises.map((f) => (
              <tr
                key={f.id}
                style={{ borderBottom: '0.5px solid #f0f0f0' }}
                className="hover:bg-[#fafafa] transition-colors"
              >
                <td className="px-4 py-3 text-[13px] text-[#111] font-medium">
                  {f.name}
                </td>
                <td className="px-4 py-3 text-[13px] text-[#666]">
                  {f.segment || '—'}
                </td>
                <td className="px-4 py-3 text-[12px] text-[#666] font-mono whitespace-nowrap">
                  {formatInvestmentRange(
                    f.minimumInvestment,
                    f.maximumInvestment,
                  )}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge isActive={f.isActive} />
                </td>
                <td className="px-4 py-3 text-right whitespace-nowrap">
                  <Link
                    href={`/admin/franquias/${f.slug}`}
                    className="text-[12px] font-medium hover:underline"
                    style={{ color: '#E25E3E' }}
                  >
                    Editar →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const QUICK_LINKS = [
  { label: 'Gerenciar Franquias', href: '/admin/franquias' },
  { label: 'Gerenciar Usuários', href: '/admin/franqueados' },
  { label: 'Notícias', href: '/admin/noticias' },
  { label: 'Segmentos ABF', href: '/admin/segmentos-abf' },
  { label: 'Patrocinados', href: '/admin/patrocinados' },
  { label: 'Big Numbers', href: '/admin/big-numbers' },
]

function QuickAccessGrid() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {QUICK_LINKS.map((l) => (
        <Link
          key={l.href}
          href={l.href}
          className="group bg-white rounded-xl border border-[#e5e5e5] hover:border-[#E25E3E] transition-colors px-4 py-4 flex items-center justify-between"
        >
          <span className="text-[13px] font-medium text-[#111]">{l.label}</span>
          <span
            className="text-[14px] transition-colors"
            style={{ color: '#999' }}
          >
            →
          </span>
        </Link>
      ))}
    </div>
  )
}

export default function AdminDashboardPanel() {
  const { token, payload } = useAuth()
  const { franchises } = useFranchises()

  const newsQuery = useQuery(newsQueries.list({ page: 1, limit: 1 }))
  const totalNews = newsQuery.data?.total ?? 0

  const usersQuery = useQuery(
    userQueries.list({
      role: 'members',
      page: 1,
      limit: 1,
      search: '',
      token: token ?? '',
    }),
  )
  const totalUsers =
    (usersQuery.data as { total?: number } | undefined)?.total ?? 0

  const totalFranchises = franchises.length
  const missingLogos = franchises.filter((f) => !f.logoUrl).length
  const coverage =
    totalFranchises > 0
      ? Math.round(((totalFranchises - missingLogos) / totalFranchises) * 100)
      : 0

  const recent = [...franchises]
    .sort((a, b) => {
      const aTime = a.createdAt ? new Date(a.createdAt).getTime() : 0
      const bTime = b.createdAt ? new Date(b.createdAt).getTime() : 0
      return bTime - aTime
    })
    .slice(0, 5)

  return (
    <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 md:py-8 space-y-8">
      <div>
        <p
          className="uppercase font-semibold mb-1.5"
          style={{ color: '#999', fontSize: '10px', letterSpacing: '1.5px' }}
        >
          Visão geral
        </p>
        <h2 className="font-display text-[24px] md:text-[28px] font-semibold text-[#111] tracking-tight leading-tight">
          Olá, {payload?.name ?? 'Admin'}
        </h2>
      </div>

      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatsCard
          label="Franquias"
          value={formatNumber(totalFranchises)}
          hint="total cadastradas"
        />
        <StatsCard
          label="Usuários"
          value={formatNumber(totalUsers)}
          hint="membros ativos"
        />
        <StatsCard
          label="Notícias"
          value={formatNumber(totalNews)}
          hint="publicadas"
        />
        <StatsCard
          label="Logos faltando"
          value={formatNumber(missingLogos)}
          hint={`${coverage}% de cobertura`}
          accent={missingLogos > 0}
        />
      </section>

      <section>
        <BloombergSectionHeader
          title="Franquias recentes"
          extra={
            <Link
              href="/admin/franquias"
              className="text-[11px] font-medium uppercase"
              style={{ color: '#E25E3E', letterSpacing: '0.8px' }}
            >
              Ver todas →
            </Link>
          }
        />
        <RecentFranchisesTable franchises={recent} />
      </section>

      <section>
        <BloombergSectionHeader title="Acesso rápido" />
        <QuickAccessGrid />
      </section>
    </div>
  )
}
