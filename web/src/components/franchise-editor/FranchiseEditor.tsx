'use client'

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { ArrowLeft } from 'lucide-react'
import type { Franchise } from '@/src/schemas/franchises/Franchise'
import FranchiseStatusBanner from '@/src/components/franqueadores/panels/franchises/FranchiseStatusBanner'
import InfoTab from './tabs/InfoTab'
import InvestmentTab from './tabs/InvestmentTab'
import MediaTab from './tabs/MediaTab'
import BusinessModelsTab from './tabs/BusinessModelsTab'

type TabKey = 'info' | 'investment' | 'media' | 'businessModels'

interface TabDef {
  key: TabKey
  label: string
}

const TABS: TabDef[] = [
  { key: 'info', label: 'Informações gerais' },
  { key: 'investment', label: 'Investimento' },
  { key: 'media', label: 'Mídia' },
  { key: 'businessModels', label: 'Modelos de negócio' },
]

interface FranchiseEditorProps {
  franchise: Franchise
  token: string
  userRole: string
}

export default function FranchiseEditor({
  franchise,
  token,
  userRole,
}: FranchiseEditorProps) {
  const [activeTab, setActiveTab] = useState<TabKey>('info')

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
  const logoSrc = franchise.logoUrl
    ? franchise.logoUrl.startsWith('http')
      ? franchise.logoUrl
      : `${apiUrl}${franchise.logoUrl}`
    : null

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 md:px-10 py-6">
      <Link
        href="/franqueador/minhas-franquias"
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-4"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Voltar pro painel
      </Link>

      <header className="mb-6 flex items-start gap-4 flex-wrap">
        <div className="w-14 h-14 bg-white rounded-[12px] border border-border/50 flex items-center justify-center shrink-0 p-2">
          {logoSrc ? (
            <Image
              src={logoSrc}
              alt={franchise.name}
              width={56}
              height={56}
              className="object-contain w-full h-full"
              unoptimized
            />
          ) : (
            <span className="text-2xl" aria-hidden="true">
              🏢
            </span>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl sm:text-3xl font-bold text-foreground truncate">
            {franchise.name}
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Editando os dados da franquia
          </p>
        </div>
      </header>

      <div className="mb-6">
        <FranchiseStatusBanner
          status={franchise.status}
          franchiseName={franchise.name}
        />
      </div>

      <div className="flex gap-6 flex-col md:flex-row">
        <aside className="md:w-60 md:shrink-0">
          <nav
            aria-label="Abas do editor"
            className="flex md:flex-col gap-1 overflow-x-auto md:overflow-visible pb-2 md:pb-0 md:sticky md:top-24"
          >
            {TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={
                  activeTab === tab.key
                    ? 'whitespace-nowrap md:whitespace-normal px-4 py-2 rounded-lg text-sm font-medium bg-primary/10 text-primary text-left'
                    : 'whitespace-nowrap md:whitespace-normal px-4 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground text-left'
                }
                aria-current={activeTab === tab.key ? 'page' : undefined}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </aside>

        <section className="flex-1 min-w-0 bg-white rounded-2xl border border-border/50 p-5 sm:p-6 md:p-8 shadow-sm">
          {activeTab === 'info' && (
            <InfoTab
              franchise={franchise}
              token={token}
              userRole={userRole}
            />
          )}
          {activeTab === 'investment' && (
            <InvestmentTab franchise={franchise} token={token} />
          )}
          {activeTab === 'media' && (
            <MediaTab franchise={franchise} token={token} />
          )}
          {activeTab === 'businessModels' && (
            <BusinessModelsTab franchise={franchise} token={token} />
          )}
        </section>
      </div>
    </div>
  )
}
