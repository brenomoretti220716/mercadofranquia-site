# Fatia 1.10 — Reviews completos

**Data da spec:** 28 de abril de 2026
**Autor:** Breno Moretti (decisões) + Claude (estruturação)
**Sessão original:** 2026-04-28 (deploy Fatia 1.8 + bug fix Reputação + spec 1.10)
**Pré-requisito:** Fatia 1.8 mergeada (PR #8) e estado vazio da Reputação commitado

---

## Resumo executivo

Implementação completa do sistema de avaliações da Mercado Franquia. Atualmente a tabela `Review` existe e tem dados (incluindo o seed de validação no `cacau-show`), mas falta o caminho de criação/edição/moderação completo.

Esta fatia entrega:

1. **Avaliar uma franquia** — qualquer user logado escreve review
2. **Editar a própria avaliação** — review é "viva", atualiza ao longo do tempo
3. **Página dedicada `/avaliações`** — lista completa paginada
4. **Resposta da marca** — franqueador responde reviews
5. **Solicitação de remoção** — franqueador contesta review com justificativa via admin
6. **Painel admin** — fila de remoções com aprovar/rejeitar

Premissa crítica: **não quebrar reviews existentes**. O seed atual da Cacau Show (7 reviews + 1 response do "Itamar" feito com user `breno.moretti`) precisa continuar renderizando.

---

## 1. Regras de negócio consolidadas

| # | Tema | Decisão | Justificativa |
|---|---|---|---|
| 1 | Quem avalia | Qualquer user logado | Decisão Breno — abrir pra todos |
| 2 | 1 review por user/franquia | Sim, edita a existente (unique parcial `authorId+franchiseId WHERE isActive=true`) | Mantém integridade (1 voz por user) + permite atualização ao longo do tempo |
| 3 | Anonymous flag | **Remover** (campo continua no DB pra retro-compat, UI dropa) | Decisão Breno |
| 4 | Moderação | Direto, sem aprovação prévia | Decisão Breno — confia no fluxo de "solicitar remoção" pra contestações |
| 5 | Verificação franqueado | Self-declared | Decisão Breno — sem fricção |
| 6 | Quem responde como marca | Qualquer user FRANCHISOR vinculado à franquia | Decisão Breno |
| 7 | Autor deleta própria | Direto (hard delete) | Princípio LGPD — dados do user, ele decide |
| 8 | Franqueador pede remoção | Vai pra fila admin com justificativa (soft delete via `isActive=false`) | Evita franqueador apagar reviews ruins arbitrariamente |
| 9 | Anti-spam | Rate limit 5 reviews/user/dia | Recomendação Claude — guardrail mínimo, sem fricção |
| 10 | Ordenação | Fixa: mais recente primeiro | Padrão de mercado (Booking, Reclame Aqui). Sem volume pra justificar toggles |
| 11 | % recomendam | (4★ + 5★) / total | Padrão Booking |
| 12 | Tamanho comentário | Min 30 / max 1000 chars | Evita "bom" sem valor + livros longos |
| 13 | Edição preserva data? | Mantém createdAt + adiciona updatedAt + mostra "(editado)" | Transparência editorial |
| 14 | Página /avaliações | 10 reviews/página, paginação WSJ-style (← 1 2 3 … 10 →) | Já existe no design system |
| 15 | Edição: pode mudar rating? | Sim, pode mudar tudo | Se mudou de opinião, mudou. Recalcula agregado |
| 16 | Indicador "(editado)" | Aparece quando `updatedAt > createdAt + 1min` | Tolerância pra evitar falso positivo no save inicial |

---

## 2. Mudanças no banco de dados

### 2.1 Nova migration: `review_v2`

```sql
-- 1. Adicionar updatedAt à Review
ALTER TABLE "Review"
  ADD COLUMN "updatedAt" TIMESTAMP(3);

-- Backfill: reviews existentes recebem updatedAt = createdAt
UPDATE "Review" SET "updatedAt" = "createdAt" WHERE "updatedAt" IS NULL;

ALTER TABLE "Review"
  ALTER COLUMN "updatedAt" SET NOT NULL,
  ALTER COLUMN "updatedAt" SET DEFAULT CURRENT_TIMESTAMP;

-- 2. Unique parcial: 1 review ATIVA por user/franquia
-- Soft-deleted (isActive=false) não bloqueia nova review do mesmo user
CREATE UNIQUE INDEX "Review_author_franchise_active_idx"
  ON "Review" ("authorId", "franchiseId")
  WHERE "isActive" = true;

-- 3. Tabela ReviewRemovalRequest (fila de remoções pra admin)
CREATE TABLE "ReviewRemovalRequest" (
  id SERIAL PRIMARY KEY,
  "reviewId" INTEGER NOT NULL REFERENCES "Review"(id) ON DELETE CASCADE,
  "requestedBy" VARCHAR(191) NOT NULL REFERENCES "User"(id),
  reason TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
  "adminNote" TEXT,
  "reviewedBy" VARCHAR(191) REFERENCES "User"(id),
  "reviewedAt" TIMESTAMP(3),
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "ReviewRemovalRequest_status_check"
    CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED'))
);

CREATE INDEX "ReviewRemovalRequest_status_idx" ON "ReviewRemovalRequest" (status);
CREATE INDEX "ReviewRemovalRequest_review_idx" ON "ReviewRemovalRequest" ("reviewId");
```

### 2.2 Notas críticas

- **Coluna `anonymous` permanece** no DB pra não quebrar reviews legadas. Backend ignora ao serializar/criar (sempre `false` em novos).
- **Coluna `isActive` já existe** (default `true`). Soft delete usa esse campo.
- **Unique parcial** é importante: se admin oculta review (`isActive=false`), user pode escrever nova. Se fosse unique total, ficaria preso à oculta pra sempre.
- **Backfill obrigatório do `updatedAt`** antes de aplicar NOT NULL.
- **CHECK constraint do status** segue o padrão Prisma legacy (com nome explícito) — preservar pra futuras migrations não quebrarem.

---

## 3. Endpoints backend

### 3.1 User-facing

```
POST   /reviews
  Body: { franchiseId, rating (1-5), comment, isFranchisee }
  Auth: qualquer user logado
  Validações:
    - comment: 30-1000 chars
    - rating: 1-5
    - rate limit: 5/dia/user (HTTP 429 se excedido)
    - 1 review ativa por user/franquia (HTTP 409 se já existe)
  Side effect: recalcular Franchise.reviewCount/ratingSum/averageRating

PATCH  /reviews/{id}
  Body: { rating?, comment?, isFranchisee? }
  Auth: só o autor da review
  Side effect: 
    - updatedAt = NOW()
    - recalcular Franchise.* se rating mudou

DELETE /reviews/{id}
  Auth: só o autor (hard delete real)
  Side effect: recalcular Franchise.*

GET    /franchises/{slug}/reviews?page=1&limit=10
  Auth: público
  Response: 
    {
      reviews: [...],
      totalPages, currentPage, totalCount,
      averageRating, recommendPercent,
      countByRating: { "5": N, "4": N, ... }
    }
  Default: page=1, limit=10, ordem desc por createdAt

GET    /reviews/me/franchise/{slug}
  Auth: user logado
  Response: review existente do user nessa franquia (ou null)
  Uso: pré-preencher modal de edição
```

### 3.2 Brand response

```
POST   /reviews/{id}/response
  Body: { content }
  Auth: user com role FRANCHISOR vinculado à franquia da review
  Validação: 1 response por review (HTTP 409 se já tem)

PATCH  /reviews/{id}/response
  Body: { content }
  Auth: mesmo FRANCHISOR
  Side effect: updatedAt = NOW()

DELETE /reviews/{id}/response
  Auth: mesmo FRANCHISOR
```

### 3.3 Removal flow

```
POST   /reviews/{id}/removal-request
  Body: { reason }
  Auth: FRANCHISOR vinculado à franquia
  Validação: 1 request PENDING por review (HTTP 409 se já existe pendente)
  Side effect: nenhum imediato — review continua visível até admin decidir
```

### 3.4 Admin

```
GET    /admin/review-removals?status=PENDING
  Auth: ADMIN
  Response: lista com review + autor + franquia + requester + reason + createdAt

POST   /admin/review-removals/{id}/approve
  Body: { adminNote? }
  Auth: ADMIN
  Side effect:
    - Review.isActive = false
    - ReviewRemovalRequest.status = APPROVED
    - reviewedBy = adminId, reviewedAt = NOW()
    - recalcular Franchise.*

POST   /admin/review-removals/{id}/reject
  Body: { adminNote? }
  Auth: ADMIN
  Side effect:
    - ReviewRemovalRequest.status = REJECTED
    - reviewedBy = adminId, reviewedAt = NOW()
```

### 3.5 Helper de agregação

Criar service compartilhado `recalculate_franchise_aggregates(franchise_id)` que roda:

```python
def recalculate_franchise_aggregates(db, franchise_id):
    result = db.execute(
        select(
            func.count(Review.id).label('count'),
            func.sum(Review.rating).label('sum'),
            func.avg(Review.rating).label('avg')
        ).where(
            Review.franchiseId == franchise_id,
            Review.isActive == True
        )
    ).one()
    
    db.execute(
        update(Franchise).where(Franchise.id == franchise_id).values(
            reviewCount=result.count or 0,
            ratingSum=result.sum or 0,
            averageRating=float(result.avg) if result.avg else None
        )
    )
    db.commit()
```

Chamar após qualquer INSERT/UPDATE/DELETE em Review que afete `isActive=true` ou rating.

---

## 4. Frontend — 3 entregas

### 4.1 Modal `ReviewCreateEditModal`

**Localização:** `web/src/components/franquias/reviews/ReviewCreateEditModal.tsx`

**Comportamento:**
- Detecta automaticamente: criar OU editar (busca review existente via `GET /reviews/me/franchise/{slug}`)
- Se já existe: pré-preenche form, botão "Atualizar avaliação"
- Se não existe: form vazio, botão "Publicar avaliação"

**Form fields:**
- **Rating:** 5 estrelas clicáveis com hover preview (Fraunces italic accent-600 quando preenchidas)
- **isFranchisee:** checkbox "Sou franqueado dessa marca"
- **Comment:** textarea com contador "30 / 1000" no canto inferior direito (cor vai pra accent-700 abaixo do mín, ink-500 entre min-max, accent-700 acima do max)
- **Botões:** Cancelar (ghost) + Publicar/Atualizar (accent-600 sólido)

**Estados:**
- Loading inicial (busca review existente)
- Form ready
- Submitting (botão disabled + loader)
- Success (toast + close modal + refresh página)
- Error (toast com mensagem do backend)

**Reusado em:**
- Botão "+ Avaliar essa franquia" no landing (`ReputacaoLanding.tsx` em ambos estados — vazio + preenchido)
- Página `/avaliacoes` (botão "Adicionar avaliação")
- Botão "Editar minha avaliação" quando user já tem review

### 4.2 Página `/ranking/[slug]/avaliacoes`

**Rota:** `web/src/app/ranking/[franquia]/avaliacoes/page.tsx`

**Estrutura:**

```
┌─────────────────────────────────────────────────┐
│ ← Voltar para Cacau Show                        │  link de retorno
│                                                 │
│ Avaliações                                      │  h1 Fraunces 64px
│                                                 │
│ ──────────────────────────────────────────────  │
│                                                 │
│ 4.7   ★ ★ ★ ★ ★                                 │  stat row (igual landing)
│       124 avaliações · 87% recomendam           │
│                                                 │
│ [Todas (124)][5★ (78)][4★ (24)][3★ (12)]...     │  filtros (clicáveis)
│                                                 │
│ ──────────────────────────────────────────────  │
│                                                 │
│ ★★★★★  Itamar L.                  17 abr 2026   │  reviews (10/pág)
│ Investi em uma loja em 2023... (editado)        │
│ ┌───────────────────────────────────────────┐   │
│ │ RESPOSTA DA MARCA · há 11 dias            │   │  response box
│ │ Itamar, valeu pelo depoimento...          │   │
│ └───────────────────────────────────────────┘   │
│ [Editar] [Excluir]                              │  só se for o autor logado
│ [Responder] [Solicitar remoção]                 │  só se for FRANCHISOR
│                                                 │
│ ──────────────────────────────────────────────  │
│ (mais 9 reviews iguais)                         │
│                                                 │
│ Mostrando 1-10 de 124    ← 1 2 3 4 … 13 →       │  paginação WSJ
│                                                 │
└─────────────────────────────────────────────────┘
│                                                 │
│ + Adicionar avaliação                           │  CTA fixa no fim (ou sticky?)
└─────────────────────────────────────────────────┘
```

**Comportamento:**
- Click em filtro de estrelas: filtra (ou desfilta se já ativo)
- Click em paginação: troca página sem reload (Next router)
- "Editar"/"Excluir" só aparecem se `review.authorId === currentUser.id`
- "Responder"/"Solicitar remoção" só aparecem se `currentUser.role === 'FRANCHISOR'` E `franquia.franchisorId === currentUser.id`
- "(editado)" aparece se `updatedAt > createdAt + 60s`
- SEO: meta tags com `noindex` (página dinâmica, não vale ranking)

### 4.3 Painel admin `/admin/review-removals`

**Rota:** `web/src/app/admin/review-removals/page.tsx`

**Estrutura:**

```
┌─────────────────────────────────────────────────┐
│ Solicitações de remoção                         │
│                                                 │
│ [Pendentes (5)][Aprovadas (12)][Rejeitadas (3)] │  tabs filtro
│                                                 │
│ ──────────────────────────────────────────────  │
│                                                 │
│ #14 · Cacau Show                  29 abr 2026   │
│                                                 │
│ Review original (Roberto S., 1★ há 12 dias):    │
│ "Marca terrível, péssimo suporte..."            │
│                                                 │
│ Solicitante: João da Cacau Show (FRANCHISOR)    │
│ Justificativa:                                  │
│ "Roberto nunca foi nosso franqueado, está       │
│  difamando a marca. Anexei e-mails que provam   │
│  que ele não consta no nosso sistema."          │
│                                                 │
│ [Aprovar (ocultar)] [Rejeitar (manter)]         │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Modal de decisão:** click em "Aprovar"/"Rejeitar" abre modal com campo `adminNote` (opcional) + confirmação.

---

## 5. Outros pontos integrados ao fluxo

### 5.1 Wire dos botões da Fatia 1.8 (que ficaram placeholder)

Após 1.10.2, voltar nos arquivos:

- `ReputacaoLanding.tsx` — botão "+ Avaliar essa franquia" ganha `onClick={() => openModal()}`
- `ReputacaoLanding.tsx` (estado preenchido) — link "Ver todas as N avaliações →" ganha `href={/ranking/${slug}/avaliacoes}`

Os comentários TODO da Fatia 1.8 facilitam encontrar esses pontos.

### 5.2 Lista admin no painel franqueador

Adicionar na sidebar do franqueador um item "Minhas avaliações" que leva pra view consolidada de reviews da franquia (todas), com:
- Botão "Responder" pras sem response
- Botão "Solicitar remoção" pra qualquer uma

Pode ficar em fatia separada (1.10.6?) — não é blocker do fluxo principal.

### 5.3 Cleanup do bloco Reputação no landing

Quando `1.10.2` for live:
- Botão "+ Avaliar essa franquia" funciona em ambos estados (vazio e preenchido)
- Remover atributos `disabled`, `opacity: 0.5`, `cursor: 'not-allowed'`
- Remover `title="Em breve"`

---

## 6. Plano de fatiamento — 5 subfatias

| Sub | Escopo | Tipo | Tempo |
|---|---|---|---|
| **1.10.1** | DB migration + endpoints CRUD básicos (POST/PATCH/DELETE Review) + helper recalculate_aggregates + endpoint GET /reviews/me/franchise/{slug} + remover anonymous da serialização | Backend-only PR | 1h |
| **1.10.2** | Modal `ReviewCreateEditModal` + wire no botão "+ Avaliar essa franquia" do landing (cacau-show + estado vazio) | Frontend-only PR | 1.5h |
| **1.10.3** | Página `/ranking/[slug]/avaliacoes` + endpoint GET /franchises/{slug}/reviews paginado + wire do link "Ver todas" | Full-stack PR | 1.5h |
| **1.10.4** | Endpoints brand response (POST/PATCH/DELETE) + UI de responder/editar response na página /avaliacoes | Full-stack PR | 1h |
| **1.10.5** | Endpoint removal-request + página admin `/admin/review-removals` + UI "Solicitar remoção" no painel franqueador + ALTER no Review.isActive | Full-stack PR | 1.5h |

**Total estimado: 6.5h focadas**, 5 PRs independentes.

### 6.1 Compatibilidade backward

Cada subfatia é independente. Se 1.10.4 atrasa, 1.10.3 já está em prod servindo. A página /avaliacoes funciona sem brand response no início (response box só renderiza quando existe).

### 6.2 Pré-requisito antes de 1.10.1

- ✅ Fatia 1.8 mergeada (PR #8)
- ✅ Estado vazio da Reputação commitado e em prod
- ✅ Botões "+ Avaliar" + "Ver todas" escondidos/disabled na 1.8 (estado conhecido pra wire na 1.10)

---

## 7. Pontos descartados (decididos mas não vão entrar)

| Item | Razão |
|---|---|
| Upload de foto na review | Adia — complica modal e backend. Volta em fatia futura se demanda real aparecer |
| Reviews em vídeo | Não — complexidade fora de escala pro mercado-alvo |
| Verificação de email do franqueado | Não — fricção desnecessária. Self-declared funciona |
| Upvotes/downvotes (Yelp-style) | Não — sem volume crítico que justifique |
| Tradução automática | Não — mercado brasileiro monolíngue |
| Reviews com tags ("ROI", "Suporte", "Treinamento") | Não — UX complexa demais pro valor agregado |
| Captcha | Não — login obrigatório já é guardrail suficiente |
| Filtro de palavras proibidas | Não — fluxo de "solicitar remoção" cobre |
| Notificações por email (review ganha, response chega) | Adia — fatia separada (não blocker) |
| Edição abusiva (limite de edições) | Adia — overhead pra problema que talvez nunca apareça |

---

## 8. Decisões pendentes pra próxima sessão

Antes de codar 1.10.1, precisa:

1. **Vincular Franchise a User FRANCHISOR** — como o backend sabe que `cacau-show` pertence a `joão@cacaushow.com`? Existe campo `franchisorId` ou tabela `FranchisorFranchise`? Verificar antes de codar endpoints de response/removal.
2. **Role FRANCHISOR vs CANDIDATE** — confirmar que o role atual no DB é `FRANCHISOR` (memórias mencionam ambos `FRANCHISOR` e `CANDIDATE` em sessões diferentes).
3. **Auth dependency** — qual o pattern de `Depends(get_current_user)` no FastAPI? Já existe `require_franchisor_profile` — confirmar uso.
4. **Toast component** — qual lib o frontend usa? `sonner`? Custom? Confirmar antes de implementar success/error states.

---

## 9. Backlog acumulado (pós Fatia 1.8 + 1.10)

Itens que **continuam pendentes** após 1.10:

1. **Rotação senha mf_user** (URGENTE — exposta em múltiplas sessões)
2. **Habilitar lint/prettier no `npm run build` regular** (pegou erro só no build:deploy)
3. **Refactor enum `FranchisorRequestStatus` duplicado** (constants.ts vs FranchisorRequest.ts)
4. **Bug `FranchisorEditing.tsx`** (cnpj/phone null check)
5. **Cleanup HubSpot test contacts**
6. **Remover seed de teste do cacau-show em prod** (quando primeira review real entrar) — comando:
   ```sql
   DELETE FROM "Review" WHERE "franchiseId" = 'cme6mfpmf004ueh0sjwl3h7qv' AND "authorId" = '0fe3a5ff-361d-4fc1-bb3f-e4f95fdc4aaa';
   UPDATE "Franchise" SET "reviewCount"=0, "ratingSum"=0, "averageRating"=NULL WHERE slug='cacau-show';
   ```
7. **Backend hook SQLAlchemy event listener** pra evitar dados órfãos no futuro (alternativa: trigger Postgres)
8. **Notificações por email** (review ganha → franqueador, response chega → autor)
9. **Painel franqueador "Minhas avaliações"** (1.10.6 implícita)

---

## 10. Apêndice — checklist pra Claude Code (próxima sessão)

```
[ ] Ler spec inteira (este arquivo)
[ ] Confirmar pré-requisitos das decisões pendentes (seção 8)
[ ] Verificar estado atual do DB de prod (cacau-show ainda com 7 reviews + 1 response)
[ ] Verificar PR #8 mergeado e estado vazio Reputação em prod
[ ] Iniciar 1.10.1 (backend-only) com migration Alembic
[ ] Aplicar migration local + EC2
[ ] E2E browser local pra cada subfatia antes de deploy
[ ] Documentar mudanças nas memórias após cada subfatia
[ ] Atualizar HANDOFF.md ao fim
```
