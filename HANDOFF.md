# Handoff — Mercadofranquia

## Estado atual (27/04/2026)

Branch: `feat/fatia-1-8-handoff-editorial` — pronta pra PR

### Fatia 1.8 — Página pública editorial v10 — COMPLETA

11 blocos no padrão editorial completo, ordem definida pelo funil de decisão do investidor:

- **Banner** full-width (placeholder hachurado quando `bannerUrl` null)
- **Hero**: logo lado a lado com h1 96px Instrument Serif, hero-meta inline desktop / vertical mobile, KPI strip 3 cols (Investimento / Payback / Unidades), CTA único laranja
- **Modelos**: cards bege adaptativos
  - Cenário A (sem modelos): ficha técnica enxuta com 5 linhas (Investimento / Payback / Faturamento / Área / Capital de giro)
  - Cenário B (com modelos): cards bege flutuando com gap 16px, 5 métricas-chave per-modelo
- **Diferenciais**: lista numerada editorial
- **Sobre a marca**: text-block 16px ink-900
- **Vídeo**: player 16/9 max-width 900px, embed direto pra YouTube, play button laranja em fallback (link out)
- **Perfil ideal**: text-block
- **Como funciona**: stepper com numeração Instrument Serif italic 64px laranja, `<ol>/<li>` semantic
- **Galeria**: grid responsivo (4 cols desktop, 2 mobile)
- **Reputação**: stat row + filtro star bar (Todas + 5/4/3/2/1 estrelas com counts) + 5 reviews destacados + link "Ver todas" pra página dedicada (Fatia 1.10)
- **Lead form**: 2 colunas dark com bullets editoriais Direto / Análise / LGPD, submit stub com toast (backend Hubspot fica pra fatia futura)

### Backend novo (Fatia 1.8.1 incorporada)

`BusinessModel` ganhou **11 campos financeiros novos** via 3 migrations encadeadas:

- `c4d8e9a1b3f2` — 9 campos: `franchiseFee`, `royalties`, `advertisingFee`, `workingCapital`, `setupCapital`, `averageMonthlyRevenue`, `storeArea`, `calculationBaseRoyaltie`, `calculationBaseAdFee`
- `e7a3f1d8b9c2` — `investment` (total per-modelo) + `payback` (meses)
- `b5a2c91e7f4d` — `profitability` (% rentabilidade média)

Outras melhorias backend:

- Endpoint `/api/franchises/{slug}/ranking` corrigido pra retornar `businessModels` e `reviews` (bug histórico — não passava `include_relations=True`)
- Endpoint `/api/franchises/{slug}` ganhou `author: { id, name } | null` na serialização de Review (mascarado server-side quando anonymous=true) + `responses[]` com `_load_response_authors` batch-load
- Schema Zod TS atualizado: `BusinessModel` com 11 campos novos, `Review` com `author` em vez de `authorName`, `Franchise` com `reviewCount/ratingSum/favoritesCount`
- `serializers.py` exposto `calculationBaseRoyaltie` + `calculationBaseAdFee` que estavam silenciados
- Seed dev `pizza-do-joao` populado com dataset completo (3 modelos com 11 campos cada, 4 reviews, 1 response, mídias placeholders)

### Documentação

Mockup target: `docs/mockups/pagina_publica_franquia_v10_handoff.html`
Plan: `docs/superpowers/plans/2026-04-27-fatia-1-8-handoff-editorial.md`
Seed dev: `deploy/ec2/scripts/dev/seed_reviews_pizza_joao.py` + `README.md`

---

## Backlog

### Fatia 1.9 — Sistema de ranges agregados (PRIORIDADE)

Os 9 campos secundários do `BusinessModel` (`franchiseFee`, `royalties`, `advertisingFee`, `workingCapital`, `setupCapital`, `setupCapital`, `calculationBaseRoyaltie`, `calculationBaseAdFee`) estão **ocultos da página pública** por enquanto. São coletados pra alimentar futuro sistema de ranges:

- Calcular min/max desses campos a partir dos modelos cadastrados
- Criar bloco "Indicadores gerais da rede" mostrando ranges como "Royalties: 4,5%–6%", "Capital de giro: R$ 25k–R$ 50k"
- Lógica adaptativa: 1 modelo = valor único, 2+ = range
- Decisão técnica: runtime aggregation no backend (mais simples) vs colunas materializadas no Franchise (mais rápido leitura)

### Fatia 1.10 — Página dedicada de avaliações

Quando a franquia tem mais de 5 reviews, o bloco Reputação na landing mostra as 5 mais relevantes + link "Ver todas as N avaliações →" pra uma rota dedicada (ainda não criada).

Quando virar prioridade:

- Rota nova: `/ranking/[franquia]/avaliacoes`
- Reutiliza componentes do bloco Reputação (`repStat`, `starbar`, `repList`)
- Paginação numérica WSJ-style (`1 · 2 · 3 ... 25`)
- Sort dropdown (`Mais recentes` / `Melhor avaliados` / `Pior avaliados`)
- Filtros persistentes via query string (`?rating=5&sort=recent`) — o link da landing já passa o filtro star bar ativo
- Schema.org `Review` markup pra SEO
- Meta tags dinâmicos por franquia (title/description com nome da rede + rating médio)
- Endpoint backend novo: `GET /api/franchises/{slug}/reviews?page=1&limit=20&rating=5&sort=recent`

### Fatia 1.8.2 — Editor de franquia (campos novos)

Atualizar editor pra coletar os novos campos do `BusinessModel`:

- `investment`, `payback`, `profitability` (5 métricas-chave da página pública)
- + os 9 campos secundários da Fatia 1.8.1 (alimentando a Fatia 1.9)

Também atualizar `routers/business_models.py:_serialize` (endpoint legacy `/api/business-models/franchise/{slug}`) pra retornar todos esses campos — hoje só `serialize_business_model` em `serializers.py` (consumido por `/api/franchises/{slug}` e `/ranking`) está atualizado.

### Outros backlogs herdados

- Bug `FranchisorEditing.tsx` (cnpj/phone null check)
- Refactor enum `FranchisorRequestStatus` duplicado
- Rotação de credenciais expostas (Postgres `mf_user`, AWS keys, `JWT_SECRET`)
- Backend Hubspot integration pro submit do LeadFormLanding (hoje stub com toast)
