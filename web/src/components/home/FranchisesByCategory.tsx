'use client'

import { Pagination } from '@/src/components/ui/Pagination'
import { franchiseQueries } from '@/src/queries/franchises'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import FranchiseCategoryCard from './FranchiseCategoryCard'

interface FranchisesByCategoryProps {
  category: string
  segment?: string
  subsegment?: string
  excludeSubsegment?: string
  minInvestment?: string
  maxInvestment?: string
  isFiltered?: boolean
  onVerMais?: () => void
}

const SKELETON_COUNT_DEFAULT = 5
const SKELETON_COUNT_FILTERED = 6

const FranchisesByCategory = ({
  category,
  segment,
  subsegment,
  excludeSubsegment,
  minInvestment,
  maxInvestment,
  isFiltered = false,
  onVerMais,
}: FranchisesByCategoryProps) => {
  const [page, setPage] = useState(1)
  const limit = isFiltered ? 6 : 5

  const { data, isLoading, isFetching } = useQuery(
    franchiseQueries.paginated({
      page,
      limit,
      segment: segment ?? category,
      subsegment,
      excludeSubsegment,
      minInvestment,
      maxInvestment,
    }),
  )

  const franchises = data?.data || []
  const total = data?.total ?? 0
  const skeletonCount = isFiltered
    ? SKELETON_COUNT_FILTERED
    : SKELETON_COUNT_DEFAULT

  const handlePageChange = (next: number) => setPage(next)

  return (
    <div id={`category-${category}`} className="mb-8 md:mb-12">
      <h3 className="text-2xl md:text-3xl font-bold text-[#6B7280] mb-4 md:mb-6">
        {category}
      </h3>

      {(isFiltered ? isLoading || isFetching : isLoading) ? (
        <div
          className={
            isFiltered
              ? 'grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-2'
              : 'flex gap-2 overflow-x-auto snap-x snap-mandatory scroll-smooth scrollbar-hide -mx-4 px-4 md:mx-0 md:px-0 md:grid md:grid-cols-5 lg:grid-cols-6 md:overflow-visible'
          }
        >
          {Array.from({ length: skeletonCount }).map((_, i) => (
            <div
              key={i}
              className={`animate-pulse ${isFiltered ? '' : 'shrink-0 w-[28vw] md:w-auto'}`}
            >
              <div className="w-full h-[100px] md:h-[110px] bg-secondary rounded-xl border border-border mb-1.5" />
              <div className="h-3 bg-secondary rounded w-3/4" />
            </div>
          ))}
        </div>
      ) : franchises.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          Nenhuma franquia encontrada nesta categoria
        </p>
      ) : (
        <>
          <div
            className={
              isFiltered
                ? 'grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-2 pb-2'
                : 'flex gap-2 overflow-x-auto snap-x snap-mandatory scroll-smooth scrollbar-hide -mx-4 px-4 md:mx-0 md:px-0 md:grid md:grid-cols-5 lg:grid-cols-6 md:overflow-visible pb-2'
            }
          >
            {franchises.map((franchise) => (
              <FranchiseCategoryCard
                key={franchise.id}
                slug={franchise.slug}
                name={franchise.name}
                logoUrl={franchise.logoUrl}
                thumbnailUrl={franchise.thumbnailUrl}
              />
            ))}

            {!isFiltered && onVerMais && (
              <button
                onClick={onVerMais}
                className="shrink-0 w-[28vw] md:w-auto h-[100px] md:h-[110px] snap-start flex flex-col items-center justify-center rounded-xl
                border border-border/60 hover:border-[#E25F3E] hover:text-[#E25F3E]
                transition-colors text-xs font-medium text-[#171726] gap-1.5 cursor-pointer"
              >
                <span className="text-lg">→</span>
                Ver mais
              </button>
            )}
          </div>

          {isFiltered && (
            <Pagination
              page={page}
              total={total}
              limit={limit}
              onPageChange={handlePageChange}
              scrollToId={`category-${category}`}
              scrollMarginTop={96}
            />
          )}
        </>
      )}
    </div>
  )
}

export default FranchisesByCategory
