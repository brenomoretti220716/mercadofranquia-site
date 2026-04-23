'use client'

import Api from '@/src/api/Api'
import { Pagination } from '@/src/components/ui/Pagination'
import { Franchise } from '@/src/schemas/franchises/Franchise'
import { Review } from '@/src/schemas/franchises/Reviews'
import { getClientAuthCookie } from '@/src/utils/clientCookie'
import { useSuspenseQuery } from '@tanstack/react-query'
import Image from 'next/image'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { useState } from 'react'
import { Pencil, ExternalLink } from 'lucide-react'
import AdminCommentPanel from '../comments-controll/AdminCommentPanel'

const fetchFranchiseById = async (id: string): Promise<Franchise> => {
  const response = await fetch(Api(`/franchises/${id}`), {
    method: 'GET',
  })

  if (!response.ok) {
    throw new Error(`Response status: ${response.status}`)
  }

  const result = await response.json()
  return result.data
}

// ✅ Função para buscar reviews separadamente (paginadas)
const fetchReviews = async (
  franchiseId: string,
  page: number,
  limit: number,
): Promise<{
  data: Review[]
  pagination: { page: number; limit: number; total: number; totalPages: number }
}> => {
  const response = await fetch(
    Api(`/reviews/admin/franchise/${franchiseId}?page=${page}&limit=${limit}`),
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getClientAuthCookie()}`,
      },
    },
  )

  if (!response.ok) {
    if (response.status === 404) {
      console.log('📝 No reviews found for franchise:', franchiseId)
      return {
        data: [],
        pagination: { page, limit, total: 0, totalPages: 0 },
      }
    }
    throw new Error(`Response status: ${response.status}`)
  }

  const result = await response.json()
  return {
    data: (result.data || []) as Review[],
    pagination: result.pagination ?? {
      page,
      limit,
      total: result.total ?? result.data?.length ?? 0,
      totalPages:
        result.total && result.total > 0 ? Math.ceil(result.total / limit) : 0,
    },
  }
}

export default function AdminSelectedFranchise() {
  const params = useParams()
  const router = useRouter()
  const franchiseId = params.franquia as string
  const [page, setPage] = useState(1)
  const limit = 4

  // React Query para buscar franquia específica
  const { data: franchise } = useSuspenseQuery({
    queryKey: ['franchise', franchiseId],
    queryFn: () => fetchFranchiseById(franchiseId),
    staleTime: 1000 * 60 * 5, // 5 minutos
    refetchOnWindowFocus: false,
  })

  // ✅ React Query para buscar reviews separadamente
  const { data: reviewsResult, refetch: refetchReviews } = useSuspenseQuery({
    queryKey: ['franchise-reviews', franchiseId, page, limit],
    queryFn: () => fetchReviews(franchiseId, page, limit),
    staleTime: 1000 * 60 * 5,
    refetchOnWindowFocus: false,
  })

  const reviews = reviewsResult?.data ?? []
  const total = reviewsResult?.pagination.total ?? reviews.length

  // Função para voltar à lista
  const handleBackToList = () => {
    router.push('/admin/franquias')
  }

  // ✅ Função para alternar status da review
  const handleToggleReviewStatus = async (
    reviewId: number,
    newStatus: boolean,
  ) => {
    try {
      // Refetch das reviews para atualizar a lista
      await refetchReviews()
      console.log(
        `Review ${reviewId} ${newStatus ? 'ativada' : 'desativada'} com sucesso!`,
      )
    } catch (error) {
      console.error('Erro ao atualizar lista de reviews:', error)
    }
  }

  // Loading/Erro: tratados via Suspense/ErrorBoundary na rota

  // No franchise found
  if (!franchise) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <div className="text-gray-500 text-lg mb-4">
          Franquia não encontrada
        </div>
        <button
          onClick={handleBackToList}
          className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
        >
          Voltar à lista
        </button>
      </div>
    )
  }

  return (
    <>
      <div className="flex items-center gap-4 m-10 mb-0">
        <button
          onClick={handleBackToList}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Voltar à lista
        </button>
      </div>

      <FranchiseAdminSummary franchise={franchise} />

      <div id="admin-franchise-reviews-panel">
        <AdminCommentPanel
          reviews={reviews}
          franchiseName={franchise.name}
          onToggleReviewStatus={handleToggleReviewStatus}
        />
      </div>
      <div className="flex justify-center my-10">
        <Pagination
          page={page}
          total={total}
          limit={limit}
          onPageChange={setPage}
          scrollToId="admin-franchise-reviews-panel"
        />
      </div>
    </>
  )
}

interface FranchiseAdminSummaryProps {
  franchise: Franchise
}

function FranchiseAdminSummary({ franchise }: FranchiseAdminSummaryProps) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
  const logoSrc = franchise.logoUrl
    ? franchise.logoUrl.startsWith('http')
      ? franchise.logoUrl
      : `${apiUrl}${franchise.logoUrl}`
    : null

  return (
    <div className="mx-4 sm:mx-6 md:mx-10 my-6">
      <div className="bg-white rounded-2xl border border-border/50 p-5 sm:p-6 shadow-sm">
        <div className="flex items-start gap-4 flex-wrap">
          <div className="w-16 h-16 bg-white rounded-xl border border-border/50 flex items-center justify-center shrink-0 p-2">
            {logoSrc ? (
              <Image
                src={logoSrc}
                alt={franchise.name}
                width={64}
                height={64}
                className="object-contain w-full h-full"
                unoptimized
              />
            ) : (
              <span className="text-3xl" aria-hidden>
                🏢
              </span>
            )}
          </div>

          <div className="flex-1 min-w-0">
            <h2 className="text-xl sm:text-2xl font-semibold text-foreground truncate">
              {franchise.name}
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              /{franchise.slug ?? franchise.id} · status {franchise.status ?? '—'}
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-2 sm:items-center">
            {franchise.slug && (
              <Link
                href={`/franqueador/franquias/${franchise.slug}/editar`}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90"
              >
                <Pencil className="h-4 w-4" aria-hidden />
                Editar dados da franquia
              </Link>
            )}
            {franchise.status === 'APPROVED' && franchise.slug && (
              <Link
                href={`/ranking/${franchise.slug}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 border border-border/60 text-sm font-medium text-muted-foreground hover:text-foreground rounded-lg"
              >
                Ver no site
                <ExternalLink className="h-4 w-4" aria-hidden />
              </Link>
            )}
          </div>
        </div>

        <p className="text-xs text-muted-foreground mt-4">
          A edição dos dados da franquia (informações, investimento, mídia,
          modelos de negócio) agora é feita pelo mesmo editor que o franqueador
          usa. Como admin, você tem acesso total — inclusive pra alterar o nome
          após aprovação.
        </p>
      </div>
    </div>
  )
}
