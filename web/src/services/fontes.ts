import Api from '@/src/api/Api'
import { getClientAuthCookie } from '@/src/utils/clientCookie'

export type SyncStatus = 'ok' | 'erro' | 'nunca'

export interface MacroSource {
  codigo: string
  nome: string
  fonte: 'BCB' | 'IBGE'
  tabela: 'MacroBcb' | 'MacroIbge' | 'PmcIbge' | 'CagedBcb'
  total: number
  /** MAX(data) da tabela de dados — informativo. Não afeta o status pill. */
  ultimo_registro: string | null
  /** createdAt da última linha em MacroSyncLog pra essa fonte. Usado pro daysSince. */
  ultima_sync: string | null
  /** status da última linha em MacroSyncLog (ou 'nunca' se não há log). */
  sync_status: SyncStatus
  duracao_ms: number | null
  registros_inseridos: number | null
}

export interface AbfSource {
  periodo: string
  ano: number
  trimestre: number | null
  status: string
  created_at: string | null
}

export interface FontesStatus {
  macro: MacroSource[]
  abf: AbfSource[]
}

export async function fetchFontesStatus(): Promise<FontesStatus> {
  const token = getClientAuthCookie()
  if (!token) throw new Error('No authentication found')

  const response = await fetch(Api('/fontes/admin/status'), {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(
      `Failed to fetch fontes status: ${response.status} ${response.statusText}`,
    )
  }

  return (await response.json()) as FontesStatus
}
