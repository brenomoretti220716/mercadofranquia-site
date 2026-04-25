import {
  FranchisorRequest,
  FranchisorRequestStatus,
} from '@/src/schemas/users/FranchisorRequest'
import { formatDateToBrazilian } from '@/src/utils/dateFormatters'
import { useUserById } from '@/src/hooks/users/useUserById'

interface FranchisorRequestsTableRowProps {
  request: FranchisorRequest
  onViewClick: (request: FranchisorRequest) => void
}

const statusColors = {
  [FranchisorRequestStatus.PENDING]: 'bg-yellow-100 text-yellow-800',
  [FranchisorRequestStatus.UNDER_REVIEW]: 'bg-blue-100 text-blue-800',
  [FranchisorRequestStatus.APPROVED]: 'bg-green-100 text-green-800',
  [FranchisorRequestStatus.REJECTED]: 'bg-red-100 text-red-800',
  [FranchisorRequestStatus.CANCELLED]: 'bg-gray-100 text-gray-800',
}

const statusLabels = {
  [FranchisorRequestStatus.PENDING]: 'Pendente',
  [FranchisorRequestStatus.UNDER_REVIEW]: 'Em Análise',
  [FranchisorRequestStatus.APPROVED]: 'Aprovado',
  [FranchisorRequestStatus.REJECTED]: 'Rejeitado',
  [FranchisorRequestStatus.CANCELLED]: 'Cancelada',
}

const modeLabels = {
  NEW: 'Marca nova',
  EXISTING: 'Reivindicação',
}

const modeColors = {
  NEW: 'bg-indigo-100 text-indigo-800',
  EXISTING: 'bg-purple-100 text-purple-800',
}

export default function FranchisorRequestsTableRow({
  request,
  onViewClick,
}: FranchisorRequestsTableRowProps) {
  const { data: user, isLoading: isLoadingUser } = useUserById(request.userId)
  const formatDate = formatDateToBrazilian

  return (
    <div className="flex bg-[#f6f6f9] border-b border-gray-200 hover:bg-gray-50 transition-colors items-center">
      {/* Marca Column */}
      <div className="w-[20%] px-6 py-4">
        <div
          className="text-sm font-medium text-gray-900 truncate"
          title={request.streamName}
        >
          {request.streamName}
        </div>
      </div>

      {/* Tipo Column */}
      <div className="w-[15%] px-6 py-4 text-center">
        <span
          className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${modeColors[request.mode]}`}
        >
          {modeLabels[request.mode]}
        </span>
      </div>

      {/* Franquia Vinculada (só em EXISTING) Column */}
      <div className="w-[20%] px-6 py-4 text-center">
        {request.franchise ? (
          <div
            className="text-sm text-gray-900 truncate"
            title={request.franchise.name}
          >
            {request.franchise.name}
          </div>
        ) : (
          <div className="text-xs text-gray-400">—</div>
        )}
      </div>

      {/* Usuário Column */}
      <div className="w-[20%] px-6 py-4 text-center">
        {isLoadingUser ? (
          <div className="text-sm text-gray-500">Carregando...</div>
        ) : user ? (
          <div>
            <div className="text-sm text-gray-900 truncate" title={user.name}>
              {user.name}
            </div>
            <div className="text-xs text-gray-500 truncate" title={user.email}>
              {user.email}
            </div>
          </div>
        ) : (
          <div className="text-sm text-gray-500">Usuário não encontrado</div>
        )}
      </div>

      {/* Status Column */}
      <div className="w-[10%] px-6 py-4 text-center">
        <span
          className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${statusColors[request.status]}`}
        >
          {statusLabels[request.status]}
        </span>
      </div>

      {/* Data Column */}
      <div className="w-[8%] px-6 py-4 text-center">
        <div className="text-sm text-gray-900">
          {formatDate(request.createdAt)}
        </div>
      </div>

      {/* Ações Column */}
      <div className="w-[7%] px-6 py-4 text-center">
        <button
          onClick={() => onViewClick(request)}
          className="text-[#E25E3E] hover:text-[#c04e2e] font-medium text-sm transition-colors"
        >
          Ver
        </button>
      </div>
    </div>
  )
}
