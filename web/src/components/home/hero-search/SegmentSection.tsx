'use client'

import { SEGMENTS } from '@/src/schemas/segments/segments'
import { useState } from 'react'
// py-2 (8px × 2) + text-sm line-height (20px)
const ITEM_HEIGHT = 36

export interface SegmentSectionProps {
  open: boolean
  onToggle: () => void
  onFocus: () => void
  selectedSegment: string
  onSearch: () => void
  isFocused: boolean
  isDimmed?: boolean
}

export function SegmentSection({
  open,
  onToggle,
  onFocus,
  selectedSegment,
  onSearch,
  isFocused,
  isDimmed = false,
}: SegmentSectionProps) {
  const triggerCta = 'Em qual segmento deseja investir?'

  return (
    <div
      className={`h-full flex items-center cursor-pointer transition-colors duration-200 ${
        isDimmed ? 'hover:bg-white/5' : ''
      }`}
      onClick={() => {
        onToggle()
        onFocus()
      }}
    >
      <div className="flex items-center gap-2 px-3 md:px-4 min-w-0">
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-white/30 shrink-0"
        >
          <rect x="3" y="3" width="7" height="7" />
          <rect x="14" y="3" width="7" height="7" />
          <rect x="3" y="14" width="7" height="7" />
          <rect x="14" y="14" width="7" height="7" />
        </svg>
        <input
          type="text"
          placeholder="Segmento"
          value={selectedSegment}
          readOnly
          className={`w-full text-[13px] font-normal bg-transparent outline-none cursor-pointer ${
            selectedSegment
              ? 'text-[#ccc]'
              : 'text-transparent placeholder:text-[#555]'
          }`}
        />
      </div>
    </div>
  )
}

// ─── Dropdown panel content (rendered by HeroSearch in the unified panel) ───

export interface SegmentDropdownPanelProps {
  onSegmentSelect: (segment: string) => void
}

export function SegmentDropdownPanel({
  onSegmentSelect,
}: SegmentDropdownPanelProps) {
  const [hoveredIndex, setHoveredIndex] = useState(-1)

  return (
    <div className="p-1.5" onMouseLeave={() => setHoveredIndex(-1)}>
      {SEGMENTS.map((segment, index) => (
        <button
          key={index}
          type="button"
          onClick={() => onSegmentSelect(segment)}
          onMouseEnter={() => setHoveredIndex(index)}
          className={`w-full text-left px-3 py-2 rounded-md transition-colors duration-150 text-sm ${
            hoveredIndex === index ? 'bg-[#2a2a2a] text-white' : 'text-white/80'
          }`}
        >
          {segment}
        </button>
      ))}
    </div>
  )
}
