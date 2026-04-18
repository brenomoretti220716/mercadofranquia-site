'use client'

const PILLS = [
  { label: 'Selic', value: '13,75%', arrow: '▼', color: 'text-[#E25E3E]' },
  { label: 'IPCA', value: '4,83%', arrow: '▲', color: 'text-[#4CAF50]' },
  {
    label: 'Setor franquias',
    value: 'R$ 211bi',
    arrow: '▲',
    extra: '+12,1%',
    color: 'text-[#4CAF50]',
  },
  { label: 'Redes ABF', value: '3.015', arrow: '▲', color: 'text-[#4CAF50]' },
  { label: 'Unidades', value: '227.256', arrow: '', color: 'text-white/70' },
]

export default function TickerBar() {
  return (
    <div className="bg-white">
      <div className="container mx-auto px-4 py-3 flex gap-2 overflow-x-auto scrollbar-hide md:justify-center md:overflow-visible">
        {PILLS.map((pill) => (
          <div
            key={pill.label}
            className="shrink-0 bg-[#111] rounded-lg px-3 py-2 min-w-[120px]"
          >
            <p className="text-[13px] font-bold text-white leading-tight">
              {pill.label}
            </p>
            <p className={`text-[12px] leading-tight mt-0.5 ${pill.color}`}>
              {pill.value}
              {pill.arrow && ` ${pill.arrow}`}
              {pill.extra && <span className={pill.color}> {pill.extra}</span>}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
