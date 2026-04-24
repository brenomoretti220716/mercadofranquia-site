'use client'

import { useState } from 'react'
import { Plus, Trash2, Loader2, ExternalLink } from 'lucide-react'
import ModalConfirmation from '@/src/components/ui/ModalConfirmation'
import {
  useAddFranchiseVideo,
  useDeleteFranchiseVideoUrl,
} from '@/src/hooks/franchises/useFranchisorFranchiseMutations'
import { normalizeVideoUrls } from '@/src/utils/franchiseImageUtils'

const MAX_VIDEOS = 10
const ALLOWED_HINTS = [
  'https://www.youtube.com/watch?v=...',
  'https://youtu.be/...',
  'https://vimeo.com/...',
]

function isLikelyAllowedHost(url: string): boolean {
  const trimmed = url.trim()
  if (!trimmed.startsWith('https://')) return false
  try {
    const u = new URL(trimmed)
    const host = u.hostname.toLowerCase()
    return (
      host === 'youtube.com' ||
      host === 'www.youtube.com' ||
      host === 'm.youtube.com' ||
      host === 'youtu.be' ||
      host === 'vimeo.com' ||
      host === 'www.vimeo.com' ||
      host === 'player.vimeo.com'
    )
  } catch {
    return false
  }
}

interface MediaVideoListProps {
  franchiseId: string
  videoUrls: string[] | string | null | undefined
  token: string
}

export default function MediaVideoList({
  franchiseId,
  videoUrls,
  token,
}: MediaVideoListProps) {
  const [input, setInput] = useState('')
  const [toDelete, setToDelete] = useState<string | null>(null)
  const addMutation = useAddFranchiseVideo()
  const deleteMutation = useDeleteFranchiseVideoUrl()

  const videos = normalizeVideoUrls(videoUrls)
  const busy = addMutation.isPending || deleteMutation.isPending
  const atLimit = videos.length >= MAX_VIDEOS

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    const url = input.trim()
    if (!url) return
    if (!isLikelyAllowedHost(url)) {
      alert(
        `URL inválida. Aceitamos apenas links HTTPS do YouTube ou Vimeo. Exemplos: ${ALLOWED_HINTS.join(' ; ')}`,
      )
      return
    }
    if (videos.includes(url)) {
      alert('Este vídeo já está na lista.')
      return
    }
    addMutation.mutate(
      { franchiseId, url, token },
      {
        onSuccess: () => setInput(''),
      },
    )
  }

  return (
    <section className="space-y-3">
      <div>
        <h3 className="text-base font-semibold text-foreground">Vídeos</h3>
        <p className="text-xs text-muted-foreground">
          URLs de YouTube ou Vimeo. {videos.length} de {MAX_VIDEOS} cadastrados.
        </p>
      </div>

      <form onSubmit={handleAdd} className="flex gap-2 flex-wrap">
        <input
          type="url"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Cole URL do YouTube ou Vimeo"
          disabled={busy || atLimit}
          className="flex-1 min-w-[240px] px-4 py-2 border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={busy || atLimit || input.trim().length === 0}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
        >
          {addMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <Plus className="h-4 w-4" aria-hidden />
          )}
          {atLimit ? 'Limite atingido' : 'Adicionar'}
        </button>
      </form>

      {videos.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-input bg-muted/30 p-6 text-center">
          <p className="text-sm text-muted-foreground">
            Nenhum vídeo cadastrado. Adicione links de apresentação da franquia.
          </p>
        </div>
      ) : (
        <ul className="space-y-2">
          {videos.map((url) => (
            <li
              key={url}
              className="flex items-center gap-2 justify-between border border-border/60 rounded-lg px-3 py-2 bg-white"
            >
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-sm text-foreground hover:text-primary min-w-0 flex-1 truncate"
              >
                <ExternalLink className="h-4 w-4 shrink-0" aria-hidden />
                <span className="truncate">{url}</span>
              </a>
              <button
                type="button"
                onClick={() => setToDelete(url)}
                disabled={busy}
                className="p-1.5 rounded-lg text-destructive hover:bg-destructive/5 disabled:opacity-50"
                aria-label="Remover vídeo"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
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
        action="remover este vídeo"
        text="A URL será removida da franquia. Você pode adicionar de novo depois."
        buttonText="Remover"
        isLoading={deleteMutation.isPending}
      />
    </section>
  )
}
