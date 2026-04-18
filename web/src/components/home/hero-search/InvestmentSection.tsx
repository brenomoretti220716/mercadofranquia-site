'use client'

import {
  countDigits,
  formatInvestmentNoDecimals,
  formatInvestmentWithDecimals,
  INVESTMENT_STEP,
  MAX_INVESTMENT_INPUT,
  MIN_INVESTMENT_RANGE,
  parseInvestmentFromInput,
  positionAfterNDigits,
} from '@/src/utils/investmentFormatters'
import { useEffect, useRef, useState } from 'react'
import { InvestmentRangeSlider } from './InvestmentRangeSlider'

const INPUT_LABEL_STYLE = { letterSpacing: '-1.5px' as const }

export interface InvestmentSectionProps {
  onToggle: () => void
  onFocus: () => void
  min: number
  max: number
  isFocused: boolean
  isDimmed?: boolean
  hasSelectedInvestment?: boolean
}

export function InvestmentSection({
  onToggle,
  onFocus,
  min,
  max,
  isFocused,
  isDimmed = false,
  hasSelectedInvestment = false,
}: InvestmentSectionProps) {
  const triggerDisplay = `R$ ${formatInvestmentWithDecimals(min)} - R$ ${formatInvestmentWithDecimals(max)}`
  const triggerCta = 'Qual faixa de investimento você deseja?'

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
          <line x1="12" y1="1" x2="12" y2="23" />
          <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
        </svg>
        <input
          type="text"
          placeholder="Faixa de investimento"
          value={hasSelectedInvestment ? triggerDisplay : ''}
          readOnly
          className={`w-full text-[13px] font-normal bg-transparent outline-none cursor-pointer ${
            hasSelectedInvestment
              ? 'text-[#ccc]'
              : 'text-transparent placeholder:text-[#555]'
          }`}
        />
      </div>
    </div>
  )
}

// ─── Dropdown panel content (rendered by HeroSearch in the unified panel) ───

export interface InvestmentDropdownPanelProps {
  min: number
  max: number
  onMinChange: (value: number) => void
  onMaxChange: (value: number) => void
  onFocus: () => void
}

export function InvestmentDropdownPanel({
  min,
  max,
  onMinChange,
  onMaxChange,
  onFocus,
}: InvestmentDropdownPanelProps) {
  const [tab, setTab] = useState<'bar' | 'inputs'>('inputs')
  const [minInputString, setMinInputString] = useState(() =>
    formatInvestmentNoDecimals(min),
  )
  const [maxInputString, setMaxInputString] = useState(() =>
    formatInvestmentNoDecimals(max),
  )
  const minInputRef = useRef<HTMLInputElement>(null)
  const maxInputRef = useRef<HTMLInputElement>(null)
  const nextMinCaretRef = useRef<number | null>(null)
  const nextMaxCaretRef = useRef<number | null>(null)
  const lastTabRef = useRef(tab)

  const handleMinInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    const selectionStart = e.target.selectionStart ?? value.length
    const digitsBeforeCaret = countDigits(value.substring(0, selectionStart))
    const parsed = parseInvestmentFromInput(value)
    onMinChange(parsed)
    if (parsed > max) onMaxChange(parsed)
    const formatted = formatInvestmentNoDecimals(parsed)
    nextMinCaretRef.current = positionAfterNDigits(formatted, digitsBeforeCaret)
    setMinInputString(formatted)
  }

  const handleMaxInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    const selectionStart = e.target.selectionStart ?? value.length
    const digitsBeforeCaret = countDigits(value.substring(0, selectionStart))
    const parsed = parseInvestmentFromInput(value)
    onMaxChange(parsed)
    if (parsed < min) onMinChange(parsed)
    const formatted = formatInvestmentNoDecimals(parsed)
    nextMaxCaretRef.current = positionAfterNDigits(formatted, digitsBeforeCaret)
    setMaxInputString(formatted)
  }

  const handleMinInputBlur = () =>
    setMinInputString(formatInvestmentNoDecimals(min))
  const handleMaxInputBlur = () =>
    setMaxInputString(formatInvestmentNoDecimals(max))

  useEffect(() => {
    if (nextMinCaretRef.current !== null && minInputRef.current) {
      const pos = nextMinCaretRef.current
      nextMinCaretRef.current = null
      requestAnimationFrame(() =>
        minInputRef.current!.setSelectionRange(pos, pos),
      )
    }
  }, [minInputString])

  useEffect(() => {
    if (nextMaxCaretRef.current !== null && maxInputRef.current) {
      const pos = nextMaxCaretRef.current
      nextMaxCaretRef.current = null
      requestAnimationFrame(() =>
        maxInputRef.current!.setSelectionRange(pos, pos),
      )
    }
  }, [maxInputString])

  useEffect(() => {
    if (lastTabRef.current !== tab) {
      setMinInputString(formatInvestmentNoDecimals(min))
      setMaxInputString(formatInvestmentNoDecimals(max))
    }
    lastTabRef.current = tab
  }, [min, max, tab])

  return (
    <div>
      <div
        className="relative flex max-w-[60vw] md:max-w-[20vw] mx-auto gap-0 bg-[#2a2a2a] rounded-[6px] mx-3 mt-3 mb-2 h-[36px]"
        style={{ padding: '3px' }}
      >
        <button
          type="button"
          onClick={() => setTab('inputs')}
          className={`relative z-10 flex-1 rounded-[4px] px-5 text-[13px] font-medium transition-colors duration-200 cursor-pointer ${
            tab === 'inputs'
              ? 'bg-[#E25E3E] text-white'
              : 'text-[#888] hover:text-white'
          }`}
        >
          Manual
        </button>
        <button
          type="button"
          onClick={() => setTab('bar')}
          className={`relative z-10 flex-1 rounded-[4px] px-5 text-[13px] font-medium transition-colors duration-200 cursor-pointer ${
            tab === 'bar'
              ? 'bg-[#E25E3E] text-white'
              : 'text-[#888] hover:text-white'
          }`}
        >
          Faixa
        </button>
      </div>
      <div className="px-3 pb-3 overflow-hidden">
        {tab === 'bar' ? (
          <div key="bar" className="animate-fade-in mt-4">
            <InvestmentRangeSlider
              min={min}
              max={max}
              onMinChange={(v) => {
                onMinChange(v)
                if (v > max) onMaxChange(v)
              }}
              onMaxChange={(v) => {
                onMaxChange(v)
                if (v < min) onMinChange(v)
              }}
              minBound={MIN_INVESTMENT_RANGE}
              maxBound={MAX_INVESTMENT_INPUT}
              step={INVESTMENT_STEP}
            />
          </div>
        ) : (
          <div
            key="inputs"
            className="animate-fade-in flex items-baseline gap-4"
          >
            <div className="flex-1">
              <label className="block text-[11px] font-medium text-[#888] mb-1.5">
                Investimento Mínimo
              </label>
              <input
                ref={minInputRef}
                type="text"
                placeholder="0"
                value={minInputString}
                onChange={handleMinInputChange}
                onBlur={handleMinInputBlur}
                onFocus={() => {
                  onFocus()
                  if (!minInputString) {
                    setMinInputString(formatInvestmentNoDecimals(min))
                  }
                }}
                className="w-full px-3 py-2 text-sm font-normal text-white placeholder:text-[#666] bg-[#2a2a2a] border border-[#444] rounded-md outline-none focus:border-[#E25E3E] transition-colors"
                style={INPUT_LABEL_STYLE}
              />
            </div>
            <div className="flex-1">
              <label className="block text-[11px] font-medium text-[#888] mb-1.5">
                Investimento Máximo
              </label>
              <input
                ref={maxInputRef}
                type="text"
                placeholder="0"
                value={maxInputString}
                onChange={handleMaxInputChange}
                onBlur={handleMaxInputBlur}
                onFocus={() => {
                  onFocus()
                  if (!maxInputString) {
                    setMaxInputString(formatInvestmentNoDecimals(max))
                  }
                }}
                className="w-full px-3 py-2 text-sm font-normal text-white placeholder:text-[#666] bg-[#2a2a2a] border border-[#444] rounded-md outline-none focus:border-[#E25E3E] transition-colors"
                style={INPUT_LABEL_STYLE}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
