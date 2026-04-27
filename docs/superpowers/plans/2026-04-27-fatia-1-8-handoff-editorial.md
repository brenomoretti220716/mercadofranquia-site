# Fatia 1.8 — Página pública editorial (handoff Mercado Franquia)

**Goal:** Aplicar o sistema editorial do handoff oficial Mercado Franquia na página pública de franquia em `/ranking/[franquia]`. Resultado fica fiel ao mockup `docs/mockups/pagina_publica_franquia_v10_handoff.html`.

**Branch:** `feat/fatia-1-8-handoff-editorial`

**Substitui:** PRs #4 e #5 (não mergeados, ficam OPEN no GitHub e são fechados em sessão futura).

---

## Decisões de design (confirmadas com o usuário)

1. **Review serializer:** estender `serialize_review()` em `deploy/ec2/app/serializers.py` pra retornar `author: { id, name } | null`. Mascarar `name` no backend quando `r.anonymous=True`. `selectinload(Review.author)` no GET `/franchises/{slug}`. Atualizar Zod `ReviewSchema`.
2. **Fontes ESCOPADAS pra `.landing`:** carregar IBM Plex Sans + IBM Plex Mono globalmente via `next/font` no `layout.tsx`, mas no `landing.module.css` só referenciar essas variáveis dentro do escopo `.landing`. Inter Tight permanece como fonte default do resto da plataforma (admin, editor). Backlog futuro: "Sistema editorial global" pra unificar tudo.
3. **Deletar:** `SelosStripLanding.tsx` e `HeroTagline.tsx`. Recuperáveis via git.
4. **Manter:** `CommentPanel` legado (usado pelo painel franqueador e admin). Só desplotar da landing pública.
5. **Editar `SelectedFranchise.tsx`** (não `page.tsx`, que é só Suspense wrapper).

---

## Bug do Review (descoberto durante recon, mais grave que o spec descreve)

`serialize_review()` em `deploy/ec2/app/serializers.py:109-120` retorna apenas `{ id, rating, comment, anonymous, isActive, isFranchisee, authorId, franchiseId, createdAt }`. Não vem `author`, não vem `authorName`. O Zod declara `authorName: z.string()` (required). Hoje passa despercebido porque a página pública usa `CommentPanel` legado (outro endpoint, outro shape).

**Fix nesta fatia:** estender backend pra trazer `author: { id, name } | null` (com nome mascarado server-side quando anonymous). Ajustar Zod. Ajustar pontos legados que liam `review.authorName` (`admin/panels/franchises/comments-controll`, `franqueadores/panels/franchises`, `franqueados/franchises/comments`).

---

## Campos do mockup que NÃO existem no DB

Omitir do componente, deixar `// TODO: campo X em fatia futura`.

- Tag verde "Payback baixo" no hero (cálculo vs setor)
- Hero meta "Marca registrada ✓" (campo `inpiRegistered` inexistente)
- KPI sub "Inclui royalty", "Abaixo da média do setor", "+18 nos últimos 12 meses"
- Tags "Físico/Modular/Compacto" nos modelos (campo `BusinessModel.category` inexistente)
- "Área" por modelo de negócio (`BusinessModel` só tem name/description/photoUrl)
- "% recomendam" na Reputação (não temos no DB)

---

## Fases

### Fase 0 — Setup
- [x] `git checkout -b feat/fatia-1-8-handoff-editorial`
- [x] Criar este plan file

### Fase 1 — Foundation: tokens e fontes
- [ ] Editar `web/src/app/layout.tsx`: adicionar IBM Plex Sans + IBM Plex Mono via `next/font/google`. Manter Inter Tight, JetBrains Mono, Fraunces (já existem). Adicionar variável CSS `--font-ibm-plex-sans` e `--font-ibm-plex-mono`. Wire no `<html className>`.
- [ ] Reescrever `web/src/components/franquias/landing/landing.module.css` com:
  - Tokens canônicos do v10 (paleta + tipografia + rules).
  - Container `.page` 1200px (era 720px).
  - Classes do v10: `.banner`, `.section`, `.kicker`, `.tag`, `.heroTags`, `.heroName`, `.tagline`, `.heroMeta`, `.kpiStrip`, `.kpi`, `.cta`, `.ctaGhost`, `.ctaBlock`, `.models`, `.model`, `.modelHead`, `.modelName`, `.modelRow`, `.textBlock`, `.video`, `.play`, `.steps`, `.step`, `.stepNum`, `.stepBody`, `.stepTitle`, `.stepDesc`, `.diff`, `.diffNum`, `.gallery`, `.galleryItem`, `.repStat`, `.repAvg`, `.repStars`, `.repMeta`, `.repFilters`, `.repFilter`, `.repList`, `.repItem`, `.repHeader`, `.repAuthor`, `.repAnon`, `.repWhen`, `.repText`, `.repResponse`, `.repPag`, `.pageBtn`, `.leadSection`, `.leadGrid`, `.leadLeft`, `.leadBullets`, `.leadForm`, `.leadRow`, `.leadDisclaimer`.
  - Media query 768px (mobile fallback do v10).
  - Manter classes legadas usadas por outros lugares (HeroTagline some agora, SelosStrip também).
- [ ] `cd web && npm run lint` (espera: pass)
- [ ] `cd web && npm run build` (espera: pass)
- [ ] **Commit 1:** `style(landing): aplicar tokens e fontes do handoff editorial v10`
- [ ] **PAUSA pra revisão visual do usuário antes de Fase 2**

### Fase 2 — Backend para reviews
- [ ] Estender `serialize_review()` em `deploy/ec2/app/serializers.py`:
  ```python
  def serialize_review(r: Review) -> dict[str, Any]:
      author = None
      if r.author is not None:
          author = {
              "id": r.author.id,
              "name": None if r.anonymous else r.author.name,
          }
      return {
          "id": r.id, "rating": r.rating, "comment": r.comment,
          "anonymous": r.anonymous, "isActive": r.isActive,
          "isFranchisee": r.isFranchisee, "authorId": r.authorId,
          "franchiseId": r.franchiseId, "createdAt": _iso(r.createdAt),
          "author": author,
      }
  ```
- [ ] Garantir `selectinload(Review.author)` no GET `/franchises/{slug}` (achar a query principal — provavelmente `app/routes/franchises.py` ou similar).
- [ ] Atualizar `web/src/schemas/franchises/Reviews.ts` `ReviewSchema`: trocar `authorName: z.string()` por `author: z.object({ id: z.string(), name: z.string().nullable() }).nullable()`.
- [ ] Buscar usos de `review.authorName` no frontend (`grep -r authorName web/src`) e ajustar pra `review.author?.name ?? "Anônimo"`.
- [ ] `cd web && npm run lint` (espera: pass)
- [ ] **Commit 2 (backend):** `fix(reviews): incluir author na serializacao publica de Review`
- [ ] **Commit 3 (frontend):** `fix(reviews): atualizar schema Zod e callers pra usar author.name`
- [ ] Reload do uvicorn já é automático via --reload. Se quebrar, avisar usuário.

### Fase 3 — Componentes (1 commit por componente)

#### 3.1 BannerLanding
- [ ] Atualizar classes pro novo CSS (banner / banner-text). Manter fallback hachurado.
- [ ] **Commit 4:** `feat(landing): handoff editorial em BannerLanding`

#### 3.2 HeroLanding (reescrita do zero)
- [ ] Hero-tags: render `<span className={styles.tag}>{segment}</span>` (só segmento por enquanto; outras tags são TODO).
- [ ] Kicker "Ficha da rede".
- [ ] H1 96px Fraunces com `<em>` na última palavra do nome (split simples por espaço, último token vira italic accent).
- [ ] Tagline 17px ink-900.
- [ ] Hero-meta mono uppercase: "Fundada em {franchiseStartYear}" + "Sede {headquarter}, {headquarterState}" + "{totalUnits} unidades".
- [ ] KPI strip 3 cols: Investimento (range BRL) / Payback (range meses) / Unidades em operação (number).
- [ ] 2 CTAs: laranja primário "Quero ser franqueado →" (rola pro lead) + ghost "Como funciona" (rola pro stepper). Recebe 2 callbacks.
- [ ] Drop import de HeroTagline.
- [ ] **Commit 5:** `feat(landing): handoff editorial em HeroLanding`

#### 3.3 ModelosLanding
- [ ] Drop fallback complexo (deletar a branch `if (!hasModels)` que cria card único — quem tem 0 modelos some o bloco inteiro).
- [ ] Render: kicker "Modelos" + h2 "Modelos disponíveis" (com "disponíveis" em italic accent) + grid 3 cols com nome Fraunces 26px + linhas Investimento / Payback (mono label / Fraunces value).
- [ ] Sem campo "Área" — `BusinessModel` não tem `area`. Comentário TODO.
- [ ] **NOTA:** `BusinessModel` atual só tem name/description/photoUrl. Os valores Investimento/Payback do mockup viriam por modelo, mas DB não tem. Decisão: usar valores agregados da Franchise (`min/maxInvestment`, `min/maxROI`) repetidos em cada card até backend ter colunas dedicadas. Comentário TODO no código.
- [ ] **Commit 6:** `feat(landing): handoff editorial em ModelosLanding`

#### 3.4 SobreLanding
- [ ] Drop linha de metas (foi pro hero-meta).
- [ ] Render: kicker "Sobre a marca" + h2 "Sobre a marca" (com "marca" em italic accent) + text-block 16px ink-900.
- [ ] **Commit 7:** `feat(landing): handoff editorial em SobreLanding`

#### 3.5 VideoLanding
- [ ] Render: kicker "Vídeo institucional" + h2 "Conheça a marca" + frame 16/9 max-width 900px ink-900 bg + play 72px laranja (ou iframe YT quando há url).
- [ ] **Commit 8:** `feat(landing): handoff editorial em VideoLanding`

#### 3.6 ProcessStepperLanding
- [ ] Render: kicker "Processo" + h2 "Como funciona" (com "funciona" em italic accent) + lista de steps com step-num Fraunces italic 64px laranja, step-title Fraunces 24px, step-desc 15px.
- [ ] **Commit 9:** `feat(landing): handoff editorial em ProcessStepperLanding`

#### 3.7 DifferentialsLanding
- [ ] Render: kicker "Vantagens competitivas" + h2 "Diferenciais" (palavra inteira italic accent) + lista com diff-num "01"/"02"/... mono uppercase, sem bullet quadrado.
- [ ] **Commit 10:** `feat(landing): handoff editorial em DifferentialsLanding`

#### 3.8 IdealProfileLanding
- [ ] Render: kicker "Perfil do investidor" + h2 "Perfil ideal" (com "ideal" em italic accent) + text-block 16px ink-900.
- [ ] **Commit 11:** `feat(landing): handoff editorial em IdealProfileLanding`

#### 3.9 GaleriaLanding
- [ ] Grid **4 cols** (era 3), gap 4px, fundo paper-3.
- [ ] Render: kicker "Galeria" + h2 "Veja as lojas" (com "Veja" em italic accent) + grid de 3 fotos + 4ª tile virando "+N" se há excedente.
- [ ] **Commit 12:** `feat(landing): handoff editorial em GaleriaLanding`

#### 3.10 ReputacaoLanding (CRIAR novo)
- [ ] `web/src/components/franquias/landing/ReputacaoLanding.tsx`
- [ ] Props: `reviews: Review[]`, `averageRating: number | null`, `reviewCount: number`.
- [ ] Render:
  - Kicker "Reputação" + h2 "Reputação" (palavra inteira italic accent).
  - Rep-stat: averageRating Fraunces 64px + estrelas (round half) + "{reviewCount} avaliações".
  - Filtros estrela: contagem por rating computada client-side. Botão `disabled` quando 0. Estado local `selectedRating` filtra a lista.
  - Lista 1 col: stars row (★★★★★) + author Fraunces 19px (`review.author?.name ?? "Anônimo"`) + tag "Anônimo" se `review.anonymous` + "há N dias" + texto + response opcional (review.responses[0]).
  - Paginação client-side numérica (5 por página): "Mostrando A–B de N · ← 1 2 3 … N →".
  - TODO: "% recomendam" (não existe no DB).
- [ ] **Commit 13:** `feat(landing): criar ReputacaoLanding com handoff editorial`

#### 3.11 LeadFormLanding
- [ ] Virar grid 2 cols: esquerda kicker "Próximo passo" + h2 56px "Quero saber mais" (com "saber" em italic accent #FF8A5C) + p + lead-bullets (48h / Análise / Sem custo); direita o form preservando submit stub atual.
- [ ] **Commit 14:** `feat(landing): handoff editorial em LeadFormLanding`

### Fase 4 — Cleanup
- [ ] Deletar `web/src/components/franquias/landing/ContactFooterLanding.tsx`
- [ ] Deletar `web/src/components/franquias/landing/HeroTagline.tsx`
- [ ] Deletar `web/src/components/franquias/landing/SelosStripLanding.tsx`
- [ ] Verificar via grep que nenhum outro arquivo importa esses 3 componentes.
- [ ] **Commit 15:** `chore(landing): remover componentes que sairam do v10`

### Fase 5 — Wiring final
- [ ] Atualizar `web/src/components/franqueados/franchises/panel/SelectedFranchise.tsx`:
  - Drop wrapper `${landingStyles.landing} ${landingStyles.page}` (CSS cuida do container).
  - Drop import e uso do `CommentPanel` (substituído por `ReputacaoLanding`).
  - Drop `SelosStripLanding`, `ContactFooterLanding` imports.
  - Importar `ReputacaoLanding`.
  - Nova ordem: `BannerLanding` → `HeroLanding` → `ModelosLanding` → `SobreLanding` → `VideoLanding` → `ProcessStepperLanding` → `DifferentialsLanding` → `IdealProfileLanding` → `GaleriaLanding` → `ReputacaoLanding` → `LeadFormLanding`.
  - Hero recebe 2 callbacks: `onPrimaryClick` (rola pro lead, ref existente) e `onGhostClick` (rola pro stepper, novo `processStepperRef`).
- [ ] `cd web && npm run lint`
- [ ] `cd web && npm run build`
- [ ] **Commit 16:** `feat(landing): substituir wiring publico pelo handoff editorial v10`

### Fase 6 — Validação manual (sem código)
- [ ] Comparar lado a lado: localhost:3000/ranking/pizza-do-joao vs `pagina_publica_franquia_v10_handoff.html`.
- [ ] Aguardar aprovação visual do usuário.
- [ ] Sem `git push` e sem PR.

---

## Pontos operacionais

- Backend uvicorn :4000 e frontend Next :3000 já rodando local. `--reload` do uvicorn pega mudanças em `serializers.py` automaticamente.
- Antes de cada commit: `cd web && npm run lint`. Se quebrar, corrigir.
- Antes do commit final da Fase 5: `cd web && npm run build`.
- Sem push, sem PR.
