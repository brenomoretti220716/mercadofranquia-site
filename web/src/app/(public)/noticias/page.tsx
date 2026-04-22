'use client'

import NewsPanel from '@/src/components/franqueados/news/panel/NewsPanel'

export default function News() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <main className="flex-1">
        <NewsPanel />
      </main>
    </div>
  )
}
