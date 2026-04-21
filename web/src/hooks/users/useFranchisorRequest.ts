import { franchiseKeys } from '@/src/queries/franchises'
import {
  CreateFranchisorRequestDto,
  RejectFranchisorRequestDto,
} from '@/src/schemas/users/FranchisorRequest'
import {
  approveFranchisorRequest,
  createFranchisorRequest,
  getAllFranchisorRequests,
  getMyFranchisorRequest,
  rejectFranchisorRequest,
  reopenFranchisorRequest,
} from '@/src/services/users'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from './useAuth'

// User hooks (for franchisors)

export function useMyFranchisorRequest() {
  const { token } = useAuth()

  return useQuery({
    queryKey: ['franchisor-request', 'my-request'],
    queryFn: () => getMyFranchisorRequest(token!),
    enabled: !!token,
    retry: false,
  })
}

export function useCreateFranchisorRequest() {
  const { token } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateFranchisorRequestDto) =>
      createFranchisorRequest(token!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['franchisor-request', 'my-request'],
      })
      // Caso a request seja mode=NEW, user virou FRANCHISOR imediatamente e
      // já tem Franchise PENDING — invalida também a lista de myFranchises.
      queryClient.invalidateQueries({
        queryKey: franchiseKeys.myFranchises(),
      })
    },
  })
}

// Admin hooks

export function useAllFranchisorRequests(params?: {
  page?: number
  limit?: number
  status?: string
  mode?: string
  search?: string
}) {
  const { token } = useAuth()

  return useQuery({
    queryKey: ['franchisor-requests', 'all', params],
    queryFn: () => getAllFranchisorRequests(token!, params),
    enabled: !!token,
  })
}

export function useApproveFranchisorRequest() {
  const { token } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (requestId: string) =>
      approveFranchisorRequest(token!, requestId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['franchisor-requests', 'all'],
      })
      queryClient.invalidateQueries({ queryKey: ['users'] })
      queryClient.invalidateQueries({
        queryKey: franchiseKeys.availableOptions(),
      })
    },
  })
}

export function useRejectFranchisorRequest() {
  const { token } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      requestId,
      data,
    }: {
      requestId: string
      data: RejectFranchisorRequestDto
    }) => rejectFranchisorRequest(token!, requestId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['franchisor-requests', 'all'],
      })
    },
  })
}

export function useReopenFranchisorRequest() {
  const { token } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (requestId: string) =>
      reopenFranchisorRequest(token!, requestId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['franchisor-requests', 'all'],
      })
    },
  })
}
