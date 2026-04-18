import { formatFranchiseName } from '@/src/utils/formatters'
import Image from 'next/image'
import Link from 'next/link'

interface FranchiseCategoryCardProps {
  slug: string
  name: string
  logoUrl?: string | null
  thumbnailUrl?: string | null
  className?: string
}

const FranchiseCategoryCard = ({
  slug,
  name,
  logoUrl,
  thumbnailUrl,
  className,
}: FranchiseCategoryCardProps) => {
  const imageUrl = logoUrl || thumbnailUrl
  const href = `/ranking/${slug}`

  return (
    <Link
      href={href}
      className={`block snap-start shrink-0 w-[28vw] md:w-auto ${className ?? ''}`}
    >
      <div className="w-full h-[100px] md:h-[110px] bg-white rounded-xl border border-border/60 overflow-hidden mb-1.5 flex items-center justify-center p-2 transition-all duration-200 hover:shadow-sm hover:border-border">
        {imageUrl ? (
          <Image
            src={imageUrl}
            alt={name}
            width={120}
            height={80}
            className="object-contain max-h-[80px]"
          />
        ) : (
          <span className="text-3xl">🏢</span>
        )}
      </div>
      <p className="text-[10px] md:text-[11px] leading-tight text-[#171726] dark:text-foreground px-0.5 line-clamp-2">
        {formatFranchiseName(name)}
      </p>
    </Link>
  )
}

export default FranchiseCategoryCard
