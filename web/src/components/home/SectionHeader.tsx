import Link from 'next/link'

interface SectionHeaderProps {
  title: string
  href?: string
  linkLabel?: string
}

export default function SectionHeader({
  title,
  href,
  linkLabel = 'Ver mais',
}: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-5">
      <div className="flex items-center gap-3">
        <h2 className="text-[11px] uppercase tracking-[0.8px] font-bold text-[#111]">
          {title}
        </h2>
      </div>
      {href && (
        <Link
          href={href}
          className="text-[11px] font-medium text-[#E25E3E] hover:underline"
        >
          {linkLabel} →
        </Link>
      )}
    </div>
  )
}
