const INDICATORS = [
  {
    label: 'Crescimento setor',
    value: '+12,1%',
    source: 'Fonte: ABF, 2025',
    color: 'text-[#4CAF50]',
  },
  {
    label: 'Novas redes',
    value: '+124',
    source: 'Fonte: ABF, 2025',
    color: 'text-foreground',
  },
  {
    label: 'Empregos diretos',
    value: '1,6 mi',
    source: 'Fonte: ABF, 2025',
    color: 'text-foreground',
  },
  {
    label: 'Ticket médio',
    value: 'R$ 148k',
    source: 'Fonte: ABF, 2025',
    color: 'text-foreground',
  },
]

export default function MacroIndicators() {
  return (
    <section className="bg-[#fafafa] border-b border-[#e5e5e5]">
      <div className="container mx-auto px-4 py-5">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
          {INDICATORS.map((item) => (
            <div
              key={item.label}
              className="bg-white rounded-lg border border-[#e5e5e5] px-4 py-3"
            >
              <p className="text-[10px] uppercase tracking-wide text-[#999] mb-1">
                {item.label}
              </p>
              <p className={`text-xl font-bold ${item.color}`}>{item.value}</p>
              <p className="text-[10px] text-[#bbb] mt-1">{item.source}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
