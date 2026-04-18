'use client'

import type { MacroSource, SyncStatus } from '@/src/services/fontes'
import { formatDataMacro } from '@/src/utils/formatters'

interface StatusBadgeProps {
  status: SyncStatus
  ultimaSync: string | null
}

// daysSince is derived from `ultimaSync` (MacroSyncLog.createdAt) — NEVER
// from `ultimo_registro`. See fontes.py docstring for why.
function StatusBadge({ status, ultimaSync }: StatusBadgeProps) {
  let bg = '#E8F5E9'
  let color = '#0F6E56'
  let label = 'OK'

  if (status === 'nunca') {
    bg = '#FFEBEE'
    color = '#A32D2D'
    label = 'NUNCA'
  } else if (status === 'erro') {
    bg = '#FFEBEE'
    color = '#A32D2D'
    label = 'ERRO'
  } else {
    const syncTs = ultimaSync ? new Date(ultimaSync).getTime() : 0
    const daysSince = ultimaSync
      ? Math.floor((Date.now() - syncTs) / 86_400_000)
      : Number.POSITIVE_INFINITY
    if (daysSince > 7) {
      bg = '#FFF8E1'
      color = '#854F0B'
      label = `${daysSince}d atrás`
    }
  }

  return (
    <span
      className="text-[10px] font-semibold px-2 py-0.5 rounded"
      style={{ background: bg, color }}
    >
      {label}
    </span>
  )
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('pt-BR')
  } catch {
    return iso
  }
}

interface FontesMacroTableProps {
  sources: MacroSource[]
}

export default function FontesMacroTable({ sources }: FontesMacroTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white mb-4">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left font-semibold py-2.5 px-4 text-gray-400">
              Status
            </th>
            <th className="text-left font-semibold py-2.5 px-4 text-gray-400">
              Fonte
            </th>
            <th className="text-right font-semibold py-2.5 px-4 text-gray-400">
              Registros
            </th>
            <th className="text-left font-semibold py-2.5 px-4 text-gray-400">
              Último dado
            </th>
            <th className="text-left font-semibold py-2.5 px-4 text-gray-400">
              Última sync
            </th>
          </tr>
        </thead>
        <tbody>
          {sources.map((src) => (
            <tr
              key={`${src.tabela}-${src.codigo}`}
              className="border-b border-gray-100 last:border-b-0"
            >
              <td className="py-2.5 px-4">
                <StatusBadge
                  status={src.sync_status}
                  ultimaSync={src.ultima_sync}
                />
              </td>
              <td className="py-2.5 px-4 font-medium text-[#1A1A1A]">
                {src.nome}
                <span className="ml-2 text-[10px] text-gray-400 font-normal uppercase">
                  {src.fonte}
                </span>
              </td>
              <td className="py-2.5 px-4 text-right text-gray-600 font-mono">
                {src.total.toLocaleString('pt-BR')}
              </td>
              <td className="py-2.5 px-4 text-gray-500">
                {formatDataMacro(src.ultimo_registro)}
              </td>
              <td className="py-2.5 px-4 text-gray-500">
                {formatDateTime(src.ultima_sync)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
