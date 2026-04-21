'use client'

import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { FileBarChart2, Landmark, Newspaper, Store } from 'lucide-react'
import RoundedButton from '@/src/components/ui/RoundedButton'
import Skeleton from '@/src/components/ui/skeletons/Skeleton'
import {
  FONTES_STATUS_KEY,
  useFontesStatus,
} from '@/src/hooks/fontes/useFontes'
import FontesAbfTable from './FontesAbfTable'
import FontesMacroTable from './FontesMacroTable'
import FontesPlaceholderSection from './FontesPlaceholderSection'

type SectionId = 'macro' | 'abf'

interface SectionHeaderProps {
  title: string
  icon: ReactNode
  total: number
  open: boolean
  onClick: () => void
}

function SectionHeader({
  title,
  icon,
  total,
  open,
  onClick,
}: SectionHeaderProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center justify-between w-full p-4 mb-1 rounded-xl border border-gray-200 bg-white hover:border-gray-300 transition-colors"
    >
      <div className="flex items-center gap-3">
        <span className="text-[#1A1A1A] flex items-center">{icon}</span>
        <span className="font-semibold text-[15px] text-[#1A1A1A]">
          {title}
        </span>
        <span
          className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
          style={{ background: '#FFF0ED', color: '#E25E3E' }}
        >
          {total}
        </span>
      </div>
      <span className="text-gray-400 text-xs">{open ? '▼' : '▶'}</span>
    </button>
  )
}

export default function AdminFontesPanel() {
  const { data, isPending } = useFontesStatus()
  const queryClient = useQueryClient()

  const [openSections, setOpenSections] = useState<Set<SectionId>>(
    new Set(['macro']),
  )

  const toggle = useCallback((id: SectionId) => {
    setOpenSections((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: FONTES_STATUS_KEY })
  }, [queryClient])

  // Counter reflects only macro sources (BCB/IBGE/PMC/CAGED). ABF reports
  // are a different beast — they're content, not live data sources — so
  // they stay out of the "N fontes ativas" tally.
  const totalFontesAtivas = useMemo(() => data?.macro.length ?? 0, [data])

  if (isPending) {
    return (
      <div className="flex m-10 w-auto flex-col">
        <div className="flex flex-row justify-between items-center mb-6">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-10 w-40 rounded-full" />
        </div>
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full rounded-xl mb-2" />
        ))}
      </div>
    )
  }

  return (
    <div className="flex m-10 w-auto flex-col">
      <div className="flex flex-row justify-between items-center mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-medium">Central de Fontes</h2>
          <span
            className="text-xs font-semibold px-2.5 py-0.5 rounded-full"
            style={{ background: '#FFF0ED', color: '#E25E3E' }}
          >
            {totalFontesAtivas} fontes ativas
          </span>
        </div>

        <RoundedButton
          color="white"
          hoverColor="#f5f5f5"
          textColor="#666"
          hoverTextColor="#1a1a1a"
          borderColor="#E5E5E5"
          hoverBorderColor="#E25E3E"
          text="Verificar todas"
          onClick={handleRefresh}
          type="button"
        />
      </div>

      <SectionHeader
        title="Dados Macroeconômicos"
        icon={<Landmark size={18} />}
        total={data?.macro.length ?? 0}
        open={openSections.has('macro')}
        onClick={() => toggle('macro')}
      />
      {openSections.has('macro') && data && (
        <FontesMacroTable sources={data.macro} />
      )}

      <SectionHeader
        title="Relatórios ABF"
        icon={<FileBarChart2 size={18} />}
        total={data?.abf.length ?? 0}
        open={openSections.has('abf')}
        onClick={() => toggle('abf')}
      />
      {openSections.has('abf') && data && <FontesAbfTable reports={data.abf} />}

      <FontesPlaceholderSection
        title="Franquias (Scraping)"
        icon={<Store size={18} />}
        phase="4"
      />

      <FontesPlaceholderSection
        title="Notícias"
        icon={<Newspaper size={18} />}
        phase="3"
      />
    </div>
  )
}
