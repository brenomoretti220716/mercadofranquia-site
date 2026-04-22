'use client'

import { useQuery } from '@tanstack/react-query'
import Image from 'next/image'
import Link from 'next/link'

import { getNewsImageUrl } from '@/src/components/franqueados/news/components/newsImage'
import { newsQueries } from '@/src/queries/news'
import type { NewsSchema } from '@/src/schemas/users/News'
import { formatDateToBrazilian } from '@/src/utils/dateFormatters'
import { generateSlug } from '@/src/utils/generateSlug'
import { calculateReadTime, formatReadTime } from '@/src/utils/readTime'
import SectionHeader from './SectionHeader'

const PLACEHOLDER_ARTICLES = [
  {
    id: 'ph-1',
    category: 'Mercado',
    title:
      'Setor de franquias cresce 12,1% em 2025 e atinge R$ 211 bilhões em faturamento',
    subtitle:
      'Dados do relatório anual da ABF mostram expansão acelerada mesmo com Selic elevada',
    meta: 'ABF · Relatório 2025 · 4 min leitura',
  },
  {
    id: 'ph-2',
    category: 'Análise',
    title: 'Alimentação lidera com 32% das novas redes abertas no ano',
    subtitle: null,
    meta: 'ABF · 2025 · 2 min',
  },
  {
    id: 'ph-3',
    category: 'Tendências',
    title:
      'Franquias de saúde e beleza crescem 18% — o maior salto entre todos os segmentos',
    subtitle: null,
    meta: 'ABF · 2025 · 3 min',
  },
  {
    id: 'ph-4',
    category: 'Expansão',
    title:
      'Microfranquias até R$ 135 mil respondem por 38% das novas operações',
    subtitle: null,
    meta: 'ABF · 2025 · 2 min',
  },
]

function resolveHref(item: NewsSchema) {
  if (!item.id) return '/noticias'
  return `/noticias/${generateSlug(item.title, item.id)}`
}

function formatMeta(item: NewsSchema) {
  const date = formatDateToBrazilian(item.updatedAt ?? item.createdAt)
  const readTime = formatReadTime(calculateReadTime(item.content))
  return `${date} · ${readTime}`
}

const NewsSection = () => {
  const { data, isLoading } = useQuery(newsQueries.list({ page: 1, limit: 6 }))

  const items = (data?.items ?? []).filter((item) => Boolean(item?.id))
  const hasNews = items.length > 0

  // Split: featured (first), sidebar (next 3-4), bottom row (rest)
  const featured = hasNews ? items[0] : null
  const sidebar = hasNews ? items.slice(1, 5) : []
  const bottom = hasNews ? items.slice(1, 4) : []

  return (
    <section className="py-8 md:py-12 bg-white">
      <div className="container mx-auto px-4">
        <div className="border-t-2 border-[#111] pt-4">
          <SectionHeader
            title="Notícias"
            href="/noticias"
            linkLabel="Ver todas"
          />
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
            <div className="md:col-span-3 aspect-[16/10] bg-secondary animate-pulse rounded" />
            <div className="md:col-span-2 space-y-4">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-16 bg-secondary animate-pulse rounded"
                />
              ))}
            </div>
          </div>
        )}

        {/* Placeholder (no real articles) */}
        {!isLoading && !hasNews && (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
            {/* Featured placeholder */}
            <div className="md:col-span-3">
              <div className="aspect-[16/10] bg-[#111] rounded flex items-center justify-center mb-4 relative">
                <span className="text-[#E25E3E] font-bold text-xl tracking-wider select-none">
                  MERCADO FRANQUIA
                </span>
                <span className="absolute top-3 left-3 px-2 py-0.5 bg-[#E25E3E] text-white text-[10px] font-medium uppercase">
                  {PLACEHOLDER_ARTICLES[0].category}
                </span>
                <span className="absolute top-3 right-3 px-2 py-0.5 bg-white/90 text-[10px] font-medium text-[#999]">
                  Em breve
                </span>
              </div>
              <h3 className="text-xl md:text-2xl font-bold text-[#111] mb-2 leading-tight">
                {PLACEHOLDER_ARTICLES[0].title}
              </h3>
              <p className="text-sm text-[#666] mb-2">
                {PLACEHOLDER_ARTICLES[0].subtitle}
              </p>
              <p className="text-[11px] text-[#999]">
                {PLACEHOLDER_ARTICLES[0].meta}
              </p>
            </div>

            {/* Sidebar placeholder */}
            <div className="md:col-span-2">
              <p className="text-[11px] uppercase tracking-[0.8px] font-bold text-[#E25E3E] mb-3">
                Últimas
              </p>
              <div className="divide-y divide-[#e5e5e5]">
                {PLACEHOLDER_ARTICLES.slice(1).map((ph) => (
                  <div key={ph.id} className="py-3 first:pt-0">
                    <span className="text-[10px] uppercase font-medium text-[#E25E3E]">
                      {ph.category}
                    </span>
                    <h4 className="text-sm font-semibold text-[#111] leading-snug mt-0.5">
                      {ph.title}
                    </h4>
                    <p className="text-[11px] text-[#999] mt-1">{ph.meta}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Real articles — Bloomberg layout */}
        {!isLoading && hasNews && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-8">
              {/* Featured (left 60%) */}
              {featured && (
                <Link
                  href={resolveHref(featured)}
                  className="md:col-span-3 group"
                >
                  <div className="aspect-[16/10] bg-secondary rounded overflow-hidden mb-4 relative">
                    <Image
                      src={getNewsImageUrl(
                        featured.photoUrl,
                        '/assets/news.jpg',
                      )}
                      alt={featured.title}
                      width={800}
                      height={500}
                      className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                    <span className="absolute top-3 left-3 px-2 py-0.5 bg-[#E25E3E] text-white text-[10px] font-medium uppercase">
                      {featured.category}
                    </span>
                  </div>
                  <h3 className="text-xl md:text-2xl font-bold text-[#111] mb-2 leading-tight group-hover:text-[#E25E3E] transition-colors">
                    {featured.title}
                  </h3>
                  {featured.summary && (
                    <p className="text-sm text-[#666] mb-2 line-clamp-2">
                      {featured.summary}
                    </p>
                  )}
                  <p className="text-[11px] text-[#999]">
                    {formatMeta(featured)}
                  </p>
                </Link>
              )}

              {/* Sidebar (right 40%) */}
              <div className="md:col-span-2">
                <p className="text-[11px] uppercase tracking-[0.8px] font-bold text-[#E25E3E] mb-3">
                  Últimas
                </p>
                <div className="divide-y divide-[#e5e5e5]">
                  {sidebar.map((item) => (
                    <Link
                      key={item.id}
                      href={resolveHref(item)}
                      className="block py-3 first:pt-0 group"
                    >
                      <span className="text-[10px] uppercase font-medium text-[#E25E3E]">
                        {item.category}
                      </span>
                      <h4 className="text-sm font-semibold text-[#111] leading-snug mt-0.5 group-hover:text-[#E25E3E] transition-colors line-clamp-2">
                        {item.title}
                      </h4>
                      <p className="text-[11px] text-[#999] mt-1">
                        {formatMeta(item)}
                      </p>
                    </Link>
                  ))}
                </div>
              </div>
            </div>

            {/* Bottom row: 3 secondary articles */}
            {bottom.length > 0 && (
              <div className="border-t border-[#e5e5e5] pt-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {bottom.map((item) => (
                    <Link
                      key={`bottom-${item.id}`}
                      href={resolveHref(item)}
                      className="group"
                    >
                      <span className="text-[10px] uppercase font-medium text-[#E25E3E]">
                        {item.category}
                      </span>
                      <h4 className="text-sm font-semibold text-[#111] leading-snug mt-1 group-hover:text-[#E25E3E] transition-colors line-clamp-2">
                        {item.title}
                      </h4>
                      <p className="text-[11px] text-[#999] mt-1">
                        {formatMeta(item)}
                      </p>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  )
}

export default NewsSection
