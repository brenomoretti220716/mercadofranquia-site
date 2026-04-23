import {
  addFranchiseGalleryPhotos,
  addFranchiseVideo,
  deleteFranchiseGalleryPhoto,
  deleteFranchiseLogo,
  deleteFranchiseThumbnail,
  deleteFranchiseVideoUrl,
  updateFranchisorFranchise,
  uploadFranchiseLogo,
  uploadFranchiseThumbnail,
} from '@/src/services/franchises'
import type { Franchise } from '@/src/schemas/franchises/Franchise'
import { formatErrorMessage } from '@/src/utils/errorHandlers'
import { useMutation, useQueryClient, type UseMutationOptions } from '@tanstack/react-query'
import { toast } from 'sonner'

interface UpdateFranchisorFranchiseInput {
  franchiseId: string
  payload: Record<string, unknown>
  token: string
}

function invalidateFranchise(
  queryClient: ReturnType<typeof useQueryClient>,
  franchiseId: string,
) {
  queryClient.invalidateQueries({ queryKey: ['my-franchises'] })
  queryClient.invalidateQueries({ queryKey: ['franchise', franchiseId] })
  queryClient.invalidateQueries({ queryKey: ['franchises'] })
}

export function useUpdateFranchisorFranchise() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      franchiseId,
      payload,
      token,
    }: UpdateFranchisorFranchiseInput) =>
      updateFranchisorFranchise(franchiseId, payload, token),
    onSuccess: (_data, variables) => {
      toast.success('Alterações salvas.')
      invalidateFranchise(queryClient, variables.franchiseId)
    },
    onError: (error: Error) => {
      toast.error(
        formatErrorMessage(error, 'Erro ao salvar alterações. Tente novamente.'),
      )
    },
  })
}

// ------------------------------------------------------------------
// Media mutations — Sprint 4 Fatia 2
// ------------------------------------------------------------------

interface MediaFileInput {
  franchiseId: string
  file: File
  token: string
}

interface MediaFilesInput {
  franchiseId: string
  files: File[]
  token: string
}

interface MediaUrlInput {
  franchiseId: string
  url: string
  token: string
}

interface MediaIdInput {
  franchiseId: string
  token: string
}

type MediaMutationOptions<TVars> = Omit<
  UseMutationOptions<Franchise, Error, TVars>,
  'mutationFn'
>

function buildMediaMutationConfig<TVars extends { franchiseId: string }>(
  queryClient: ReturnType<typeof useQueryClient>,
  successMsg: string,
  errorFallback: string,
) {
  return {
    onSuccess: (_data: Franchise, variables: TVars) => {
      toast.success(successMsg)
      invalidateFranchise(queryClient, variables.franchiseId)
    },
    onError: (error: Error) => {
      toast.error(formatErrorMessage(error, errorFallback))
    },
  } satisfies MediaMutationOptions<TVars>
}

export function useUploadFranchiseLogo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ franchiseId, file, token }: MediaFileInput) =>
      uploadFranchiseLogo(franchiseId, file, token),
    ...buildMediaMutationConfig<MediaFileInput>(qc, 'Logo atualizado.', 'Erro ao enviar logo.'),
  })
}

export function useDeleteFranchiseLogo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ franchiseId, token }: MediaIdInput) =>
      deleteFranchiseLogo(franchiseId, token),
    ...buildMediaMutationConfig<MediaIdInput>(qc, 'Logo removido.', 'Erro ao remover logo.'),
  })
}

export function useUploadFranchiseThumbnail() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ franchiseId, file, token }: MediaFileInput) =>
      uploadFranchiseThumbnail(franchiseId, file, token),
    ...buildMediaMutationConfig<MediaFileInput>(qc, 'Thumbnail atualizado.', 'Erro ao enviar thumbnail.'),
  })
}

export function useDeleteFranchiseThumbnail() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ franchiseId, token }: MediaIdInput) =>
      deleteFranchiseThumbnail(franchiseId, token),
    ...buildMediaMutationConfig<MediaIdInput>(qc, 'Thumbnail removido.', 'Erro ao remover thumbnail.'),
  })
}

export function useAddFranchiseGalleryPhotos() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ franchiseId, files, token }: MediaFilesInput) =>
      addFranchiseGalleryPhotos(franchiseId, files, token),
    ...buildMediaMutationConfig<MediaFilesInput>(qc, 'Fotos adicionadas.', 'Erro ao adicionar fotos.'),
  })
}

export function useDeleteFranchiseGalleryPhoto() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ franchiseId, url, token }: MediaUrlInput) =>
      deleteFranchiseGalleryPhoto(franchiseId, url, token),
    ...buildMediaMutationConfig<MediaUrlInput>(qc, 'Foto removida.', 'Erro ao remover foto.'),
  })
}

export function useAddFranchiseVideo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ franchiseId, url, token }: MediaUrlInput) =>
      addFranchiseVideo(franchiseId, url, token),
    ...buildMediaMutationConfig<MediaUrlInput>(qc, 'Vídeo adicionado.', 'Erro ao adicionar vídeo.'),
  })
}

export function useDeleteFranchiseVideoUrl() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ franchiseId, url, token }: MediaUrlInput) =>
      deleteFranchiseVideoUrl(franchiseId, url, token),
    ...buildMediaMutationConfig<MediaUrlInput>(qc, 'Vídeo removido.', 'Erro ao remover vídeo.'),
  })
}
