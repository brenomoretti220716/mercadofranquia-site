'use client'

import { useRef, useState } from 'react'
import Image from 'next/image'
import { ImagePlus, Trash2, Loader2 } from 'lucide-react'
import ModalConfirmation from '@/src/components/ui/ModalConfirmation'
import {
  useAddFranchiseGalleryPhotos,
  useDeleteFranchiseGalleryPhoto,
} from '@/src/hooks/franchises/useFranchisorFranchiseMutations'
import {
  getFranchiseImageUrl,
  normalizeGalleryUrls,
} from '@/src/utils/franchiseImageUtils'

const ACCEPTED_MIMES = 'image/jpeg,image/jpg,image/png,image/gif,image/webp'
const MAX_BYTES = 5 * 1024 * 1024
const MAX_GALLERY = 20

interface MediaGalleryManagerProps {
  franchiseId: string
  galleryUrls: string[] | string | null | undefined
  token: string
}

export default function MediaGalleryManager({
  franchiseId,
  galleryUrls,
  token,
}: MediaGalleryManagerProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const addMutation = useAddFranchiseGalleryPhotos()
  const deleteMutation = useDeleteFranchiseGalleryPhoto()
  const [toDelete, setToDelete] = useState<string | null>(null)

  const urls = normalizeGalleryUrls(galleryUrls)
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
  const remaining = Math.max(0, MAX_GALLERY - urls.length)

  const onPick = () => inputRef.current?.click()

  const onFilesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    e.target.value = ''
    if (files.length === 0) return
    const oversized = files.filter((f) => f.size > MAX_BYTES)
    if (oversized.length > 0) {
      alert(
        `Alguns arquivos ultrapassam 5MB e não serão enviados: ${oversized.map((f) => f.name).join(', ')}`,
      )
    }
    const valid = files.filter((f) => f.size <= MAX_BYTES)
    if (valid.length === 0) return
    if (valid.length > remaining) {
      alert(
        `Você tentou enviar ${valid.length} fotos mas só restam ${remaining} vagas (limite ${MAX_GALLERY}).`,
      )
      return
    }
    addMutation.mutate({ franchiseId, files: valid, token })
  }

  const busy = addMutation.isPending || deleteMutation.isPending

  return (
    <section className="space-y-3">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h3 className="text-base font-semibold text-foreground">
            Galeria de fotos
          </h3>
          <p className="text-xs text-muted-foreground">
            {urls.length} de {MAX_GALLERY} fotos. Mostra no detalhe da franquia.
            JPEG, PNG, GIF ou WebP, até 5MB cada.
          </p>
        </div>
        <button
          type="button"
          onClick={onPick}
          disabled={busy || remaining === 0}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
        >
          {addMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <ImagePlus className="h-4 w-4" aria-hidden />
          )}
          {remaining === 0 ? 'Galeria cheia' : 'Adicionar fotos'}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_MIMES}
          multiple
          onChange={onFilesSelected}
          hidden
        />
      </div>

      {urls.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-input bg-muted/30 p-8 text-center">
          <p className="text-sm text-muted-foreground">
            Nenhuma foto cadastrada. Adicione fotos pra ilustrar sua franquia.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {urls.map((u) => {
            const pretty = getFranchiseImageUrl(u)
            const src = pretty
              ? pretty.startsWith('http')
                ? pretty
                : `${apiUrl}${pretty}`
              : null
            return (
              <div
                key={u}
                className="relative aspect-square rounded-xl overflow-hidden border border-border/60 bg-white group"
              >
                {src && (
                  <Image
                    src={src}
                    alt="Foto da galeria"
                    fill
                    className="object-cover"
                    unoptimized
                  />
                )}
                <button
                  type="button"
                  onClick={() => setToDelete(u)}
                  disabled={busy}
                  className="absolute top-2 right-2 h-8 w-8 rounded-full bg-black/60 hover:bg-destructive/90 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50"
                  aria-label="Remover foto"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            )
          })}
        </div>
      )}

      <ModalConfirmation
        isOpen={!!toDelete}
        onClose={() => setToDelete(null)}
        onConfirm={() => {
          if (!toDelete) return
          deleteMutation.mutate(
            { franchiseId, url: toDelete, token },
            { onSettled: () => setToDelete(null) },
          )
        }}
        action="remover esta foto"
        text="A imagem será apagada permanentemente."
        buttonText="Remover"
        isLoading={deleteMutation.isPending}
      />
    </section>
  )
}
