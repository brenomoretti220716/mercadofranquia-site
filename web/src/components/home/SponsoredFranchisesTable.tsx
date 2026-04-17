'use client'

import Marquee from '@/src/components/ui/Marquee'
import { Franchise } from '@/src/schemas/franchises/Franchise'
import {
  formatFranchiseName,
  formatInvestmentRange,
} from '@/src/utils/formatters'
import Image from 'next/image'
import Link from 'next/link'
import StarIcon from '../icons/starIcon'

interface SponsoredFranchisesTableProps {
  franchises: Franchise[]
  onClick: (franchiseId: string) => void
}

function RatingCell({ rating }: { rating: number | null | undefined }) {
  if (rating === null || rating === undefined) {
    return <span className="text-[#ccc]">—</span>
  }
  return (
    <div className="flex items-center gap-1">
      <StarIcon width={14} height={14} color="#facc15" filled={true} />
      <span className="text-sm font-medium">{rating.toFixed(1)}</span>
    </div>
  )
}

const SponsoredFranchisesTable = ({
  franchises,
  onClick,
}: SponsoredFranchisesTableProps) => {
  return (
    <div>
      {/* Mobile View */}
      <div className="w-full md:hidden">
        <div className="flex items-center py-2">
          <div className="w-[12%] px-2 text-[10px] uppercase tracking-[0.5px] text-[#888] font-normal">
            #
          </div>
          <div className="w-[58%] px-2 text-[10px] uppercase tracking-[0.5px] text-[#888] font-normal">
            Franquia
          </div>
          <div className="w-[30%] px-2 text-[10px] uppercase tracking-[0.5px] text-[#888] font-normal">
            Rating
          </div>
        </div>

        {franchises.map((franchise) => {
          if (!franchise.slug) return null
          const position = franchise.rankingPosition || 0

          return (
            <div
              key={franchise.id}
              onClick={() => onClick(franchise.slug as string)}
              className="flex items-center cursor-pointer transition-colors hover:bg-[#fafafa] py-2.5"
              style={{ borderBottom: '0.5px solid #f0f0f0' }}
            >
              <div className="w-[12%] px-2 text-center">
                <span className="text-sm text-[#888]">{position}</span>
              </div>
              <div className="w-[58%] px-2 overflow-hidden min-w-0">
                <div className="flex items-center gap-2 min-w-0">
                  {franchise.logoUrl ? (
                    <div className="w-7 h-7 bg-white rounded flex items-center justify-center shrink-0 p-0.5">
                      <Image
                        src={franchise.logoUrl}
                        alt={franchise.name}
                        width={28}
                        height={28}
                        className="object-contain w-full h-full"
                      />
                    </div>
                  ) : (
                    <span className="text-lg shrink-0">🏢</span>
                  )}
                  <span className="text-sm font-medium text-foreground truncate">
                    {formatFranchiseName(franchise.name)}
                  </span>
                </div>
              </div>
              <div className="w-[30%] px-2">
                <RatingCell rating={franchise.averageRating} />
              </div>
            </div>
          )
        })}
      </div>

      {/* Desktop View */}
      <div className="hidden md:block">
        <table className="w-full table-fixed">
          <colgroup>
            <col className="w-[7%]" />
            <col className="w-[30%]" />
            <col className="w-[18%]" />
            <col className="w-[14%]" />
            <col className="w-[20%]" />
            <col className="w-[11%]" />
          </colgroup>
          <thead>
            <tr>
              <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-[0.5px] text-[#888] font-normal">
                #
              </th>
              <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-[0.5px] text-[#888] font-normal">
                Franquia
              </th>
              <th className="text-center px-4 py-2.5 text-[10px] uppercase tracking-[0.5px] text-[#888] font-normal">
                Rating
              </th>
              <th className="text-center px-4 py-2.5 text-[10px] uppercase tracking-[0.5px] text-[#888] font-normal">
                Unidades
              </th>
              <th className="text-center px-4 py-2.5 text-[10px] uppercase tracking-[0.5px] text-[#888] font-normal">
                Investimento
              </th>
              <th />
            </tr>
          </thead>
          <tbody>
            {franchises.map((franchise) => {
              if (!franchise.slug) return null
              const position = franchise.rankingPosition || 0

              return (
                <tr
                  key={franchise.id}
                  onClick={() => onClick(franchise.slug as string)}
                  className="cursor-pointer transition-colors hover:bg-[#fafafa]"
                  style={{ borderBottom: '0.5px solid #f0f0f0' }}
                >
                  <td className="px-4 py-3">
                    <span className="text-sm text-[#888]">{position}</span>
                  </td>
                  <td
                    className="px-4 py-3 overflow-hidden"
                    style={{ maxWidth: 0 }}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      {franchise.logoUrl ? (
                        <div className="w-9 h-9 bg-white rounded flex items-center justify-center shrink-0 p-1">
                          <Image
                            src={franchise.logoUrl}
                            alt={franchise.name}
                            width={36}
                            height={36}
                            className="object-contain w-full h-full"
                          />
                        </div>
                      ) : (
                        <span className="text-xl shrink-0">🏢</span>
                      )}
                      <Marquee className="min-w-0 flex-1">
                        <span className="text-sm font-medium text-foreground">
                          {formatFranchiseName(franchise.name)}
                        </span>
                      </Marquee>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center">
                      <RatingCell rating={franchise.averageRating} />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center text-sm text-foreground">
                    {franchise.totalUnits?.toLocaleString('pt-BR') ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-center text-sm text-foreground">
                    {formatInvestmentRange(
                      franchise.minimumInvestment,
                      franchise.maximumInvestment,
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Link
                      href={`/ranking/${franchise.slug}`}
                      onClick={(e) => e.stopPropagation()}
                      className="text-[12px] text-[#E25E3E] font-medium hover:underline"
                    >
                      Ver →
                    </Link>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div
        className="flex items-center justify-between pt-3 mt-1"
        style={{ borderTop: '0.5px solid #e5e5e5' }}
      >
        <span className="text-[12px] text-[#888]">
          Mostrando {franchises.length} de 1.409 franquias
        </span>
        <Link
          href="/ranking"
          className="text-[12px] text-[#E25E3E] font-medium hover:underline"
        >
          Ver ranking completo · 1.409 franquias →
        </Link>
      </div>
    </div>
  )
}

export default SponsoredFranchisesTable
