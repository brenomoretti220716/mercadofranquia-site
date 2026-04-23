'use client'

import { Construction } from 'lucide-react'

export default function MediaTab() {
  return (
    <div className="flex flex-col items-center justify-center text-center py-12 px-4">
      <Construction
        className="h-10 w-10 text-muted-foreground mb-4"
        aria-hidden="true"
      />
      <h2 className="text-xl font-semibold text-foreground mb-2">
        Disponível em breve
      </h2>
      <p className="text-sm text-muted-foreground max-w-md">
        O upload de logo, thumbnail, galeria e vídeo da franquia chega na
        próxima atualização do editor.
      </p>
    </div>
  )
}
