'use client'

import type { ReactNode } from 'react'

interface FontesPlaceholderSectionProps {
  title: string
  icon: ReactNode
  /** "3", "4", etc — fase da fusão em que essa seção vira real. */
  phase: string
}

export default function FontesPlaceholderSection({
  title,
  icon,
  phase,
}: FontesPlaceholderSectionProps) {
  return (
    <div className="flex items-center gap-3 p-4 mb-1 rounded-xl border border-gray-200 bg-gray-50 cursor-not-allowed select-none">
      <span className="text-gray-400">{icon}</span>
      <span className="font-semibold text-gray-500 text-[15px]">{title}</span>
      <span
        className="ml-auto uppercase font-semibold rounded px-2 py-1"
        style={{
          background: '#EEE',
          color: '#888',
          fontSize: '9px',
          letterSpacing: '0.8px',
        }}
      >
        Em breve — Fase {phase} da fusão
      </span>
    </div>
  )
}
