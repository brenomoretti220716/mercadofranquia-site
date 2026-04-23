'use client'

import { useRef, useState } from 'react'
import Image from 'next/image'
import { ImagePlus, Trash2, Loader2 } from 'lucide-react'
import ModalConfirmation from '@/src/components/ui/ModalConfirmation'
import {
  useDeleteFranchiseLogo,
  useUploadFranchiseLogo,
} from '@/src/hooks/franchises/useFranchisorFranchiseMutations'
import { getFranchiseImageUrl } from '@/src/utils/franchiseImageUtils'

const ACCEPTED_MIMES = 'image/jpeg,image/jpg,image/png,image/gif,image/webp'
const MAX_BYTES = 5 * 1024 * 1024

interface MediaLogoCardProps {
  franchiseId: string
  currentUrl: string | null | undefined
  token: string
}

export default function MediaLogoCard({
  franchiseId,
  currentUrl,
  token,
}: MediaLogoCardProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const uploadMutation = useUploadFranchiseLogo()
  const deleteMutation = useDeleteFranchiseLogo()
  const [confirmOpen, setConfirmOpen] = useState(false)

  const pretty = getFranchiseImageUrl(currentUrl)
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
  const resolved = pretty
    ? pretty.startsWith('http')
      ? pretty
      : `${apiUrl}${pretty}`
    : null

  const busy = uploadMutation.isPending || deleteMutation.isPending

  const onPick = () => inputRef.current?.click()

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    if (file.size > MAX_BYTES) {
      alert('Arquivo deve ter no máximo 5MB.')
      return
    }
    uploadMutation.mutate({ franchiseId, file, token })
  }

  return (
    <section className="space-y-3">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h3 className="text-base font-semibold text-foreground">Logo</h3>
          <p className="text-xs text-muted-foreground">
            Imagem quadrada (ex: 400x400). JPEG, PNG, GIF ou WebP até 5MB.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4 flex-wrap">
        <div className="w-24 h-24 rounded-xl border border-border/60 bg-white flex items-center justify-center overflow-hidden">
          {resolved ? (
            <Image
              src={resolved}
              alt="Logo atual"
              width={96}
              height={96}
              className="object-contain w-full h-full p-2"
              unoptimized
            />
          ) : (
            <span className="text-3xl text-muted-foreground" aria-hidden>
              🏢
            </span>
          )}
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={onPick}
            disabled={busy}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
          >
            {uploadMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <ImagePlus className="h-4 w-4" aria-hidden />
            )}
            {currentUrl ? 'Alterar logo' : 'Enviar logo'}
          </button>
          {currentUrl && (
            <button
              type="button"
              onClick={() => setConfirmOpen(true)}
              disabled={busy}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-destructive/50 text-destructive text-sm font-medium hover:bg-destructive/5 disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" aria-hidden />
              Remover
            </button>
          )}
        </div>

        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_MIMES}
          onChange={onFileChange}
          hidden
        />
      </div>

      <ModalConfirmation
        isOpen={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => {
          deleteMutation.mutate(
            { franchiseId, token },
            { onSettled: () => setConfirmOpen(false) },
          )
        }}
        action="remover o logo"
        text="Sua franquia ficará sem logo até você enviar um novo."
        buttonText="Remover"
        isLoading={deleteMutation.isPending}
      />
    </section>
  )
}
