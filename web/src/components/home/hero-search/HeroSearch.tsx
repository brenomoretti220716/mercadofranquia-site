'use client'

import { useClickOutside } from '@/src/hooks/useClickOutside'
import { MAX_INVESTMENT_INPUT } from '@/src/utils/investmentFormatters'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { InvestmentDropdownPanel, InvestmentSection } from './InvestmentSection'
import { SegmentDropdownPanel, SegmentSection } from './SegmentSection'

export interface HeroSearchFilters {
  minInvestment: number
  maxInvestment: number
  segment: string
}

// Approximate counts by max investment bracket
const INVESTMENT_COUNTS: [number, number][] = [
  [50000, 312],
  [100000, 487],
  [200000, 698],
  [300000, 821],
  [500000, 934],
  [1000000, 1102],
  [2000000, 1287],
  [Infinity, 1409],
]

const TOTAL_FRANCHISES = 1409
const SEGMENT_COUNT = 16

function estimateCount(maxInvestment: number, hasSegment: boolean): number {
  let count = TOTAL_FRANCHISES
  if (maxInvestment > 0 && maxInvestment < MAX_INVESTMENT_INPUT) {
    const bracket = INVESTMENT_COUNTS.find(([cap]) => maxInvestment <= cap)
    count = bracket ? bracket[1] : TOTAL_FRANCHISES
  }
  // Rough segment ratio: ~1/SEGMENT_COUNT of results
  if (hasSegment) {
    count = Math.max(1, Math.round(count / (SEGMENT_COUNT * 0.6)))
  }
  return count
}

const HeroSearch = () => {
  const router = useRouter()
  const [focusedSection, setFocusedSection] = useState<
    'investment' | 'segment' | null
  >(null)
  const [minInvestmentValue, setMinInvestmentValue] = useState(0)
  const [maxInvestmentValue, setMaxInvestmentValue] = useState(0)
  const [hasSelectedInvestment, setHasSelectedInvestment] = useState(false)
  const [selectedSegment, setSelectedSegment] = useState('')
  const [showSegmentDropdown, setShowSegmentDropdown] = useState(false)
  const [showInvestmentDropdown, setShowInvestmentDropdown] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const [panelStyle, setPanelStyle] = useState<{
    left: number
    width: number
  } | null>(null)

  const investmentRef = useRef<HTMLDivElement>(null)
  const segmentRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLDivElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => {
    const activeRef =
      focusedSection === 'investment'
        ? investmentRef
        : focusedSection === 'segment'
          ? segmentRef
          : null

    if (!activeRef?.current || !searchRef.current) {
      setPanelStyle(null)
      return
    }

    const sectionRect = activeRef.current.getBoundingClientRect()
    const containerRect = searchRef.current.getBoundingClientRect()

    setPanelStyle({
      left: sectionRect.left - containerRect.left,
      width: sectionRect.width,
    })
  }, [focusedSection])

  const handleClickOutside = useCallback(() => {
    setShowSegmentDropdown(false)
    setShowInvestmentDropdown(false)
    setFocusedSection(null)
  }, [])

  useClickOutside([investmentRef, segmentRef, dropdownRef], handleClickOutside)

  const handleSearch = useCallback(() => {
    const effectiveMin = minInvestmentValue > 0 ? minInvestmentValue : 0
    const effectiveMax =
      maxInvestmentValue > 0 ? maxInvestmentValue : MAX_INVESTMENT_INPUT
    const safeMin = Math.min(effectiveMin, effectiveMax)

    const params = new URLSearchParams()
    if (safeMin > 0) params.set('minInvestment', String(safeMin))
    if (effectiveMax < MAX_INVESTMENT_INPUT)
      params.set('maxInvestment', String(effectiveMax))
    if (selectedSegment) params.set('segment', selectedSegment)
    params.set('scrollToRanking', '1')

    router.push(`/ranking?${params.toString()}`)
  }, [minInvestmentValue, maxInvestmentValue, selectedSegment, router])

  const handleSegmentSelect = useCallback((segment: string) => {
    setSelectedSegment(segment)
    setShowSegmentDropdown(false)
    setFocusedSection(null)
  }, [])

  const isOpen = showInvestmentDropdown || showSegmentDropdown
  const hasFilter = hasSelectedInvestment || selectedSegment !== ''

  const estimatedCount = useMemo(
    () => estimateCount(maxInvestmentValue, selectedSegment !== ''),
    [maxInvestmentValue, selectedSegment],
  )
  const progressPct = Math.round((estimatedCount / TOTAL_FRANCHISES) * 100)

  const [dropdownVisible, setDropdownVisible] = useState(false)
  useEffect(() => {
    if (!isOpen) {
      setDropdownVisible(false)
      return
    }
    const id = requestAnimationFrame(() => setDropdownVisible(true))
    return () => cancelAnimationFrame(id)
  }, [isOpen])

  return (
    <>
      <section
        id="hero-search"
        className="bg-[#0d0d0d] relative overflow-visible py-10 md:py-14"
      >
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          {/* Eyebrow */}
          <header className="text-center mb-6 sm:mb-8">
            <p className="text-[10px] tracking-[1.5px] text-[#E25E3E]/90 font-medium mb-3">
              Inteligência de franquias
            </p>
            <h1 className="text-2xl sm:text-3xl lg:text-5xl font-bold text-white">
              Qual franquia combina com você?
            </h1>
          </header>

          <div className="max-w-3xl mx-auto z-10 relative">
            {/* Search bar */}
            <div
              ref={searchRef}
              className="relative bg-[#161616] rounded-[6px] h-[52px] flex items-center overflow-hidden"
              style={{ border: '0.5px solid #222' }}
            >
              <div ref={investmentRef} className="flex-1 min-w-0 h-full">
                <InvestmentSection
                  onToggle={() => {
                    setShowSegmentDropdown(false)
                    setShowInvestmentDropdown((prev) => !prev)
                  }}
                  onFocus={() => setFocusedSection('investment')}
                  min={minInvestmentValue}
                  max={maxInvestmentValue}
                  isFocused={focusedSection === 'investment'}
                  isDimmed={focusedSection === 'segment'}
                  hasSelectedInvestment={hasSelectedInvestment}
                />
              </div>

              <div className="h-7 w-px bg-[#222] shrink-0" />

              <div ref={segmentRef} className="flex-1 min-w-0 h-full">
                <SegmentSection
                  open={showSegmentDropdown}
                  onToggle={() => {
                    setShowInvestmentDropdown(false)
                    setShowSegmentDropdown((prev) => !prev)
                  }}
                  onFocus={() => setFocusedSection('segment')}
                  selectedSegment={selectedSegment}
                  onSearch={handleSearch}
                  isFocused={focusedSection === 'segment'}
                  isDimmed={focusedSection === 'investment'}
                />
              </div>

              <button
                onClick={handleSearch}
                className="flex items-center justify-center bg-[#E25E3E] hover:bg-[#c94e32] text-white w-[56px] h-full shrink-0 transition-colors"
                aria-label="Buscar"
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </button>
            </div>

            {/* Dropdown panel */}
            {isOpen && (
              <div
                ref={dropdownRef}
                className={
                  isMobile
                    ? 'mt-1 bg-[#161616] rounded-[6px] overflow-hidden'
                    : 'absolute mt-1 bg-[#161616] rounded-[6px] overflow-hidden z-50'
                }
                style={{
                  border: '0.5px solid #222',
                  opacity: dropdownVisible ? 1 : 0,
                  transition: 'opacity 200ms ease-out',
                  ...(isMobile
                    ? { width: 'calc(100% - 56px)' }
                    : {
                        top: '100%',
                        left: showInvestmentDropdown ? 0 : undefined,
                        right: showSegmentDropdown ? 56 : undefined,
                        width: 'calc(50% - 28px)',
                      }),
                }}
              >
                {showInvestmentDropdown && (
                  <InvestmentDropdownPanel
                    min={minInvestmentValue}
                    max={maxInvestmentValue}
                    onMinChange={(v) => {
                      setHasSelectedInvestment(v > 0 || maxInvestmentValue > 0)
                      setMinInvestmentValue(v)
                      if (v > maxInvestmentValue) setMaxInvestmentValue(v)
                    }}
                    onMaxChange={(v) => {
                      setHasSelectedInvestment(minInvestmentValue > 0 || v > 0)
                      setMaxInvestmentValue(v)
                      if (v < minInvestmentValue) setMinInvestmentValue(v)
                    }}
                    onFocus={() => setFocusedSection('investment')}
                  />
                )}

                {showSegmentDropdown && (
                  <SegmentDropdownPanel onSegmentSelect={handleSegmentSelect} />
                )}
              </div>
            )}
          </div>

          {/* Dynamic result counter */}
          <div className="max-w-3xl mx-auto mt-8 text-center">
            <div className="flex items-baseline justify-center gap-2">
              <span
                className="text-[36px] font-medium text-white font-display transition-opacity duration-300"
                style={{ letterSpacing: '-1.5px' }}
              >
                {estimatedCount.toLocaleString('pt-BR')}
              </span>
              <span className="text-[14px] text-[#555]">
                {hasFilter ? 'franquias para você' : 'redes cadastradas'}
              </span>
              {hasFilter && (
                <button
                  onClick={handleSearch}
                  className="text-[13px] text-[#E25E3E] font-medium hover:underline ml-2"
                >
                  Ver resultado →
                </button>
              )}
            </div>

            <p className="text-[12px] text-[#444] mt-1">
              {hasFilter
                ? 'Refine mais ou clique em buscar'
                : `de ${TOTAL_FRANCHISES.toLocaleString('pt-BR')} redes no Brasil`}
            </p>

            {/* Progress bar */}
            <div className="max-w-xs mx-auto mt-3">
              <div className="h-[2px] bg-[#1a1a1a] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#E25E3E] transition-all duration-500 ease-out"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <p className="text-[10px] text-[#444] mt-1">
                {progressPct}% do universo de franquias do Brasil
              </p>
            </div>
          </div>

          {/* Mini stats */}
          <div
            className="max-w-3xl mx-auto mt-6 pt-4 flex items-center justify-center gap-4 text-center"
            style={{ borderTop: '0.5px solid #1a1a1a' }}
          >
            {[
              { value: 'R$ 48k+', label: 'menor invest.' },
              { value: '16', label: 'segmentos' },
              { value: 'R$ 211bi', label: 'faturamento setor' },
            ].map((s) => (
              <div key={s.label} className="flex items-baseline gap-1">
                <span className="text-[13px] text-[#aaa] font-medium">
                  {s.value}
                </span>
                <span className="text-[10px] text-[#444]">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA cadastro */}
      <div
        className="bg-[#161616] py-2.5"
        style={{ borderTop: '0.5px solid #222' }}
      >
        <div className="container mx-auto px-4 flex items-center justify-between">
          <span className="text-[12px] text-[#555]">
            Sua franquia não está aqui?
          </span>
          <Link
            href="/cadastro"
            className="text-[12px] text-[#E25E3E] font-medium hover:underline"
          >
            Cadastre gratuitamente →
          </Link>
        </div>
      </div>
    </>
  )
}

export default HeroSearch
