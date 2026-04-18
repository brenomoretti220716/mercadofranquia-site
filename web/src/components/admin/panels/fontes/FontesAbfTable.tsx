'use client'

import type { AbfSource } from '@/src/services/fontes'

// AbfReport.status is a free-form string in the model (server_default='importado').
// Known values today: 'importado' (yellow), 'revisado' (blue), 'publicado' (green).
// Anything else falls back to the neutral yellow so we don't hide unknown states.
function statusPillStyle(status: string): { bg: string; color: string } {
  switch (status) {
    case 'publicado':
      return { bg: '#E8F5E9', color: '#0F6E56' }
    case 'revisado':
      return { bg: '#EBF5FF', color: '#2563EB' }
    default:
      return { bg: '#FFF8E1', color: '#854F0B' }
  }
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('pt-BR')
  } catch {
    return iso
  }
}

interface FontesAbfTableProps {
  reports: AbfSource[]
}

export default function FontesAbfTable({ reports }: FontesAbfTableProps) {
  if (reports.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white mb-4 p-6 text-center text-sm text-gray-500">
        Nenhum relatório ABF importado ainda.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white mb-4">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left font-semibold py-2.5 px-4 text-gray-400">
              Status
            </th>
            <th className="text-left font-semibold py-2.5 px-4 text-gray-400">
              Período
            </th>
            <th className="text-center font-semibold py-2.5 px-4 text-gray-400">
              Ano
            </th>
            <th className="text-center font-semibold py-2.5 px-4 text-gray-400">
              Trimestre
            </th>
            <th className="text-left font-semibold py-2.5 px-4 text-gray-400">
              Importado em
            </th>
          </tr>
        </thead>
        <tbody>
          {reports.map((r) => {
            const pill = statusPillStyle(r.status)
            return (
              <tr
                key={r.periodo}
                className="border-b border-gray-100 last:border-b-0"
              >
                <td className="py-2.5 px-4">
                  <span
                    className="text-[10px] font-semibold px-2 py-0.5 rounded uppercase"
                    style={{ background: pill.bg, color: pill.color }}
                  >
                    {r.status}
                  </span>
                </td>
                <td className="py-2.5 px-4 font-medium text-[#1A1A1A]">
                  {r.periodo}
                </td>
                <td className="py-2.5 px-4 text-center text-gray-600">
                  {r.ano}
                </td>
                <td className="py-2.5 px-4 text-center text-gray-600">
                  {r.trimestre ?? '—'}
                </td>
                <td className="py-2.5 px-4 text-gray-500">
                  {formatDateTime(r.created_at)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
