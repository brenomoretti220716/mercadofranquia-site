import { useQuery } from '@tanstack/react-query'
import Api from '@/src/api/Api'

export interface BusinessModel {
  id: string
  name: string
  description: string
  photoUrl: string
  franchiseId: string
  createdAt: string
  updatedAt: string

  // Fatia 1.8.1 — dataset financeiro por modelo. Todos optional/nullable
  // porque a populacao depende do endpoint:
  //   - /api/franchises/{slug} e /ranking (serialize_business_model em
  //     serializers.py) retornam os 9 campos.
  //   - /api/business-models/franchise/{slug} (router legacy
  //     business_models.py:_serialize) ainda nao retorna — sera
  //     atualizado na Fatia 1.8.2 (editor de franquia).
  // Numeric(15,2) e Numeric(5,2) viram number via _num() no backend.
  franchiseFee?: number | null
  royalties?: number | null
  advertisingFee?: number | null
  workingCapital?: number | null
  setupCapital?: number | null
  averageMonthlyRevenue?: number | null
  storeArea?: number | null
  calculationBaseRoyaltie?: string | null
  calculationBaseAdFee?: string | null

  // Fatia 1.8.1 (alembic e7a3f1d8b9c2) — investment total + payback per
  // modelo. Mesma observacao dos campos acima: so o /franchises/{slug}
  // (e /ranking) retornam; legacy /business-models/franchise/{slug}
  // ainda nao.
  investment?: number | null
  payback?: number | null
}

async function fetchBusinessModelsByFranchise(
  franchiseId: string,
): Promise<BusinessModel[]> {
  const response = await fetch(Api(`/business-models/franchise/${franchiseId}`))

  if (!response.ok) {
    throw new Error('Failed to fetch business models')
  }

  return response.json()
}

export function useBusinessModelsByFranchise(franchiseId: string) {
  return useQuery({
    queryKey: ['businessModels', franchiseId],
    queryFn: () => fetchBusinessModelsByFranchise(franchiseId),
    enabled: !!franchiseId,
  })
}

export async function fetchBusinessModelById(
  id: string,
): Promise<BusinessModel> {
  const response = await fetch(Api(`/business-models/${id}`))

  if (!response.ok) {
    throw new Error('Failed to fetch business model')
  }

  return response.json()
}

export function useBusinessModelById(id: string) {
  return useQuery({
    queryKey: ['businessModel', id],
    queryFn: () => fetchBusinessModelById(id),
    enabled: !!id,
  })
}
