# FUSÃO — Inventário & plano de migração

Documento de referência para fundir **Intelligence** (`~/Developer/mercadofranquia/`)
no **Site** (`~/Developer/mercadofranquia-site/`). Atualizado em 2026-04-18.
Este doc é leitura obrigatória antes de cada sessão de migração.

**TL;DR — números:**

| Projeto | Telas admin | Endpoints backend | Tabelas BD | Deps AI |
|---|---:|---:|---:|---|
| Intelligence | 14 (12 func + 2 redirects) | ~85 rotas FastAPI | 17 SQLite | Claude (via HTTP cru, `claude-sonnet-4-20250514`) |
| Site | 10 | ~70 rotas em 15 routers FastAPI | 26 modelos PG (21 core + 5 macro novos) | — nenhuma |

**Stack do Site em produção:** FastAPI + SQLAlchemy + PostgreSQL no EC2 +
Next.js 16. Existe um backend NestJS legado em `api/` ainda mexido
recentemente (3 arquivos modificados) — decomissionamento pendente,
ortogonal à fusão.

---

## Seção 0 — Decisões cravadas

> **Leia isto primeiro em toda sessão.** Fechado em 2026-04-18; só muda com revisão explícita.

| # | Tema | Decisão | Implicação |
|---:|---|---|---|
| 1 | **`AbfSegmentEntry`** | **DELETA INTEIRO** — tabela + router `abf_segments.py` + 6 arquivos frontend sob `web/src/**/abfSegments/**` + painel `/admin/segmentos-abf` | `/mercado` público lê dessa tabela hoje. **Reconstruir `/mercado` em cima de `AbfRevenue` + `SegmentAcronym` ANTES** do drop. Ordem forçada: ver Fase 4.5 na Seção 5. |
| 2 | **Dedupe Franquias** | **SITE MANDA.** `Franchise` atual é a verdade. Intelligence contribui apenas franquias **NOVAS** (não sobrescreve nada). Match por **nome normalizado** (lowercase, sem acento, sem pontuação). | 1.387 (Intelligence) × 1.409 (Site). Expectativa: só ~50–100 NEW. Algoritmo + função de normalização: ver subseção "Regra de match" na Fase 4 (Seção 5). |
| 3 | **Claude no EC2** | **SDK oficial `anthropic>=0.40.0`** (substitui `requests` cru do Intelligence). | Exige `ANTHROPIC_API_KEY` no `.env` do EC2. Modelo: `claude-sonnet-4-5-20250929` ou superior — validar disponibilidade no momento da Fase 1.2. |
| 4 | **NestJS (`api/`)** | **CONGELADO a partir de 2026-04-18.** Zero commits novos em `api/`. | Todo trabalho de backend daqui em diante em `deploy/ec2/app/`. Decommissionamento fica pra Fase 5. Ver Apêndice A §4.1 pra procedimento de freeze. |

---

## Seção 1 — Inventário do Intelligence

### 1.1 Backoffice — 14 telas

| Rota | O que faz | Endpoints consumidos | Tabelas SQLite | Deps ext | LOC |
|---|---|---|---|---|---:|
| `/backoffice` | Overview: 4 KPIs (notícias pendentes, publicadas, coletadas, dados) | `GET /api/admin/stats`, `GET /api/noticias/stats` | — | — | 79 |
| `/backoffice/upload` | **Extração PDF ABF via Claude** → revisão → salvar | `POST /api/backoffice/extrair`, `POST /api/backoffice/salvar` | relatorios, faturamento, indicadores, ranking, projecoes | Claude API, pdfplumber | 307 |
| `/backoffice/dashboard-dados` | 5 abas: faturamento, segmentos, macro, emprego, projeções (12+ séries) | `/api/faturamento/*`, `/api/indicadores`, `/api/projecoes`, `/api/ranking`, `/api/macro/{bcb,ibge}`, `/api/varejo/pmc`, `/api/emprego/caged`, `/api/consumidor/*` | faturamento, indicadores, projecoes, ranking, macro_bcb, macro_ibge, pmc_ibge, caged_bcb | Recharts | 130 |
| `/backoffice/editorial` | Pipeline editorial 4 estágios com regeneração IA | `/api/editorial/*` (10 rotas), `/api/imagens/refazer/*`, `/api/pipeline/rodar` | noticias_raw, noticias_fila, noticias_publicadas | Claude API | 348 |
| `/backoffice/studio` | Cards + carrosséis Instagram (5 tipos) | `/api/studio/*`, `/api/carrosseis/*`, `/api/imagens/gerar/*` | posts_instagram, carrosseis_instagram | Claude API, Pillow | 222 |
| `/backoffice/franquias` | Browse 1.387 franquias paginado | `GET /api/franquias?page=N` | franquias | — | 114 |
| `/backoffice/relatorios` | Listar/aprovar/deletar relatórios ABF | `GET /api/relatorios`, `POST /api/backoffice/salvar` (update), `DELETE /api/backoffice/excluir/{periodo}` | relatorios | — | 148 |
| `/backoffice/fontes` | 4 blocos de monitoramento (macro, ABF, franquias, notícias) com botão sync | `GET /api/fontes/status`, `POST /api/fontes/sync/{tipo}` | sync_log, relatorios, franquias, noticias_raw | — | 250 |
| `/backoffice/sistema` | Logs de sync + auditoria (tabbed) | `GET /api/sync/status`, `GET /api/audit` | sync_log, **audit_log (0 linhas)** | — | 113 |
| `/backoffice/logs` | Logs sync filtráveis + export CSV | `GET /api/sync/status` | sync_log | — | 170 |
| `/backoffice/auditoria` | Audit log filtrado por INSERT/UPDATE/DELETE | `GET /api/audit?acao=*` | audit_log (vazia) | — | 141 |
| `/backoffice/inteligencia` | Hub de links rápidos com KPI cards | `GET /api/admin/stats` | — | — | 60 |
| `/backoffice/login` | Login NextAuth credenciais | NextAuth `signIn("credentials")` | — | next-auth | 102 |
| `/backoffice/noticias`, `/backoffice/carrosseis` | Redirects → `/editorial`, `/studio` | — | — | — | ~5 |

### 1.2 `/mercado` público no Intelligence

Nenhum. `app/page.tsx` é placeholder do Next.js. Public-facing = 0.

### 1.3 Backend FastAPI — ~85 rotas em `api/main.py` (1.243 LOC, arquivo único)

Agrupadas:

- **Dados ABF (leitura):** `/api/faturamento/{anual,segmentos}`, `/api/indicadores`, `/api/ranking`, `/api/projecoes`, `/api/relatorios` → tabelas `relatorios/faturamento/indicadores/ranking/projecoes`.
- **Macro (leitura):** `/api/macro/{bcb,ibge}`, `/api/varejo/pmc`, `/api/emprego/caged`, `/api/consumidor/{painel,confianca,endividamento,massa-salarial}` → tabelas `macro_bcb/macro_ibge/pmc_ibge/caged_bcb`.
- **Backoffice ABF (escrita):** `POST /api/backoffice/extrair` (PDF + Claude), `POST /api/backoffice/salvar`, `DELETE /api/backoffice/excluir/{periodo}`.
- **Editorial:** 10 rotas em `/api/editorial/*` (fila, stats, aprovar, publicar, rejeitar, voltar_revisao, editar, refazer) + `/api/pipeline/rodar`.
- **Studio:** `/api/studio/{stats,cards,carrosseis}` + `/api/studio/{cards,carrosseis}/{id}/{aprovar,publicar,rejeitar}` + `/api/studio/cards/{id}/editar`.
- **Carrosséis:** `/api/carrosseis/gerar?tipo=*` (5 tipos), `/api/carrosseis/{id}`, `/api/carrosseis/{id}/slide/{n}`.
- **Imagens:** `/api/imagens/{gerar,refazer,status}` — Claude gera copy, Pillow renderiza.
- **Notícias legadas:** `/api/noticias/{fila,stats,slug,publicar,rejeitar}` (aliases do editorial).
- **Instagram:** `/api/instagram/{posts,card,aprovar}`.
- **Franquias:** `/api/franquias` (paginado), `/api/franquias/{slug}`, `/api/franquias/{segmentos,investimento-por-segmento}`.
- **Fontes:** `/api/fontes/status`, `/api/fontes/sync/{macro,noticias,franquias}`.
- **Admin/ops:** `/api/admin/stats`, `/api/sync/status`, `/api/audit`.

### 1.4 Schema SQLite — `api/abf.db` (~7,4 MB, 17 tabelas)

| Tabela | Linhas | Observação |
|---|---:|---|
| `relatorios` | 28 | Metadata de PDFs ABF 2018-2025 |
| `faturamento` | 133 | Faturamento por período × segmento × tipoDado |
| `indicadores` | 14 | KPIs anuais (empregos, redes, unidades, ticket) |
| `ranking` | 40 | Top franquias por unidades (2018-2024) |
| `projecoes` | ~5 | Projeções anuais |
| `macro_bcb` | 7.159 | **já migrado pro PG** (Sessão 4) |
| `macro_ibge` | 270 | **já migrado** |
| `pmc_ibge` | 1.595 | **já migrado** |
| `caged_bcb` | 870 | **já migrado** |
| `franquias` | 1.387 | ⚠️ CRÍTICO — fonte raspada, ver Seção 3 |
| `noticias_raw` | 161 | Notícias brutas de RSS/scrapers |
| `noticias_fila` | 29 | IA processou, em revisão editorial |
| `noticias_publicadas` | 2 | Publicadas (funil muito vazio) |
| `posts_instagram` | 8 | Cards Instagram |
| `carrosseis_instagram` | 6 | Carrosséis (5 tipos) |
| `sync_log` | 137 | Trilha de sync (usado, não migrar) |
| `audit_log` | **0** | Schema existe mas NUNCA foi escrito |

### 1.5 Dependências externas do Intelligence

**Backend `api/requirements.txt`:**
- `fastapi`, `uvicorn`, `pdfplumber==0.11.0`, `python-multipart`, `aiofiles`, `Pillow`, `matplotlib`
- Claude API: chamado via `requests` cru (sem SDK oficial `anthropic`). Usa `ANTHROPIC_API_KEY` + modelo `claude-sonnet-4-20250514`.

**Frontend `inteligencia/package.json`:**
- `next@16.2.1`, `react@19.2.4`, `next-auth@4.24.13`, `recharts@3.8.1`, `@tanstack/react-table`, `shadcn`, `tailwindcss@4`.

**Ortos que vão importar:** `pdfplumber`, `Pillow`, `matplotlib` (charts p/ carrosséis), Claude API. Não há SDK Anthropic hoje — pode migrar pro `anthropic` oficial na fusão.

---

## Seção 2 — Inventário do Site (admin atual)

### 2.1 Admin — 10 telas sob `/admin/*`

Root frontend em `web/src/app/(admin)/admin/**`.

| Rota | O que faz | Endpoints consumidos | Modelos PG | LOC aprox |
|---|---|---|---|---:|
| `/admin` | Dashboard (stats + rankings) | `/statistics`, `/ranking-big-numbers` | PlatformStatistics, RankingBugnumber | ~120 |
| `/admin/franquias` | CRUD franquias (list, filtros, togglestatus, review, sponsored) | `/franchises/admin/all`, `PATCH /franchises/{id}/*` | Franchise, ContactInfo, BusinessModel, FranchiseMonthlyUnits | ~250 |
| `/admin/franquias/[slug]` | Editor por franquia | `GET /franchises/{slug}`, `PATCH /franchises/{id}` | idem acima | ~300 |
| `/admin/segmentos-abf` | CRUD ABF por ano/trimestre/sigla | `/abf-segments/*` | AbfSegmentEntry | ~180 |
| `/admin/noticias` | CRUD notícias | `/news/*` | News, NewsComment | ~150 |
| `/admin/patrocinados` | Toggle sponsored + placement slots (JSONB) | `PATCH /franchises/{id}/toggle-sponsored`, `PATCH /franchises/{id}/sponsor-placements` | Franchise | ~120 |
| `/admin/big-numbers` | Top/Worst franquias por ano | `/ranking-big-numbers/admin/*` | RankingBugnumber | ~160 |
| `/admin/administradores` | User admins CRUD | `POST /users`, `GET /users/admins` | User, UserProfile | ~100 |
| `/admin/franqueadores` | Franqueadores (CNPJ, doc paths) | `/users/franchisors*` | FranchisorUser, FranchisorRequest | ~140 |
| `/admin/franqueados` | Membros (franqueados) | `/users/members` | User, UserProfile | ~100 |

### 2.2 Backend FastAPI — 15 routers em `deploy/ec2/app/routers/`

Todos montados em `main.py`. Nenhum router órfão.

| Router | Prefixo | Notas |
|---|---|---|
| `auth.py` | `/auth` | Login, reset, verify (JWT) |
| `register.py` | `/users/register` | Fluxo 2 passos (email verify + perfil) |
| `users.py` | `/users` | `/me`, profile-completion, admin sub-rotas (list admins/members/franchisors, POST admin) |
| `franchises.py` | `/franchises` | Paginado, filtros, admin CRUD, import CSV, toggle status/review/sponsored, sponsor placements |
| `franchisor_requests.py` | `/users/franchisor-request` | Solicitação de conta franqueador + approve/reject |
| `reviews.py` | `/reviews` | Avaliações franqueadas + réplicas franqueadores |
| `news.py` | `/news` | CRUD + comentários |
| `notifications.py` | `/notifications` | User notifications (read/dismiss) |
| `favorites.py` | `/favorites` | Bookmark franquias |
| `quiz.py` | `/quiz` | Quiz perfil investidor + recomendações |
| `business_models.py` | `/business-models` | Modelos de negócio por franquia |
| `abf_segments.py` | `/abf-segments` | CRUD AbfSegmentEntry |
| `big_numbers.py` | `/ranking-big-numbers` | Top/Worst (RankingBugnumber) |
| `statistics.py` | `/statistics` | Singleton PlatformStatistics (id=1) |
| `ranking.py` | `/ranking` | Top franchises por totalUnits |
| `scraping.py` | `/scraping` | Trigger scrape (admin only) |

### 2.3 PostgreSQL — 26 modelos

**Core (21):** User, UserProfile, UserVerification, ContactInfo, Franchise, Favorite, BusinessModel, FranchiseMonthlyUnits, Review, ReviewResponse, News, NewsComment, Notification, FranchisorUser, FranchisorRequest, QuizSubmission, RankingBugnumber, AbfSegmentEntry, PlatformStatistics + associação `_FranchiseFranchisees`.

**Macro novos da Sessão 3-4 (5 + log):** SegmentAcronym, AbfReport, AbfRevenue, AbfIndicator, AbfUnitsRanking, AbfProjection, MacroBcb, MacroIbge, PmcIbge, CagedBcb, MacroSyncLog.

---

## Seção 3 — Matriz de decisão

Decisões possíveis:

- **MIGRA INTEGRAL** — porta 1:1 (pequenas adaptações SQLite→PG inevitáveis).
- **MIGRA ADAPTADO** — porta mas redesenha pra se encaixar no estilo do site.
- **MIGRA + MERGE** — Intelligence tem algo que o site também tem (parcialmente) → consolida sem duplicar.
- **DESCARTA INTELLIGENCE** — não migra (já existe algo melhor no site, ou é código morto).
- **JÁ NO SITE** — produto já tem, mantém como está.
- **DELETA DO SITE** — feature existe no site mas é legado, remove.

### 3.1 Matriz (ordem: Intelligence-primeiro, depois features só-do-site)

| Feature | No Intelligence | No Site | Decisão | Justificativa |
|---|---|---|---|---|
| **Upload PDF ABF** | `/backoffice/upload` + `POST /api/backoffice/extrair` (Claude + pdfplumber) | — | **MIGRA INTEGRAL** | Ferramenta crítica de entrada de dados ABF. Sem isso, a base de relatórios vira estática |
| **Relatórios ABF** | `/backoffice/relatorios` + 3 endpoints | — | **MIGRA INTEGRAL** | Decorrência do upload. Porta pro modelo `AbfReport` já existente no PG |
| **Central de Fontes** | `/backoffice/fontes` + `GET /api/fontes/status` (4 blocos) | — | **MIGRA ADAPTADO** | Ponto de monitoramento unificado. Redesenhar usando `MacroSyncLog` que já existe |
| **Dashboard de Dados** | `/backoffice/dashboard-dados` (5 abas, 12 séries) | parcialmente em `/mercado` público | **MIGRA ADAPTADO** | Versão admin. Queries mudam: SQLite → PG (macro já migrado) |
| **Franquias (admin)** | `/backoffice/franquias` — 1.387 raspadas | `/admin/franquias` — CRUD estruturado | **MIGRA + MERGE** | ⚠️ maior risco de regressão. Site tem schema rico (50+ colunas, sponsor/JSONB); Intelligence tem massa de 1.387. Precisa estratégia de chave primária e dedupe |
| **Editorial de notícias** | `/backoffice/editorial` (4 estágios, IA) | `/admin/noticias` (CRUD básico) | **MIGRA + MERGE** | Preserva o CRUD atual; adiciona workflow IA (geração/regeneração) por cima. Alinhar schema News ↔ noticias_publicadas |
| **Studio Instagram (cards + carrosséis)** | `/backoffice/studio` + 5 tipos de carrossel | — | **MIGRA ADAPTADO (faseado)** | Alto valor mas depende de infra de geração de imagem. Considerar migrar cards primeiro, carrosséis em segunda fase |
| **Logs/Sistema** | `/backoffice/{logs,sistema,auditoria}` | — | **MIGRA ADAPTADO (unificado)** | Consolidar as 3 telas em UMA `/admin/logs` lendo `MacroSyncLog`. Auditoria descartada (ver abaixo) |
| **Audit log (tabela audit_log)** | `/backoffice/auditoria` — tabela com 0 linhas | — | **DESCARTA INTELLIGENCE** | Schema existe mas nunca foi escrito. Se precisar, constrói do zero com triggers PG |
| **Hub Inteligência** | `/backoffice/inteligencia` — só atalhos | layout admin já tem nav | **DESCARTA INTELLIGENCE** | Redundante |
| **Login NextAuth** | `/backoffice/login` | `/login` JWT próprio | **DESCARTA INTELLIGENCE** | Site tem auth integrado a User+JWT; não misturar |
| **Dashboard overview** | `/backoffice` (4 KPI cards) | `/admin` já existe | **MIGRA ADAPTADO** | Port KPIs úteis pro dashboard existente |
| **Redirects** `/backoffice/{noticias,carrosseis}` | existem | — | **DESCARTA INTELLIGENCE** | Só redirects |
| — | — | `/admin/big-numbers` (RankingBugnumber) | **DELETA DO SITE** | Sua instrução — legado/dados de teste, drop tabela + router + tela + frontend queries |
| — | — | `/admin/segmentos-abf` (AbfSegmentEntry) | **DELETA DO SITE (requer reconstrução prévia de `/mercado`)** | Decisão 1 (Seção 0). `/mercado` público lê de `AbfSegmentEntry` hoje — não dá pra dropar antes. Fase 4.5 reconstrói `/mercado` em cima de `AbfRevenue` + `SegmentAcronym`, então drop na Fase 5 |
| — | — | `/admin/patrocinados` | **JÁ NO SITE** | Feature exclusiva do site, mantém |
| — | — | `/admin/{administradores,franqueadores,franqueados}` | **JÁ NO SITE** | Gestão de usuários, não existe no Intelligence |

**Prévia das 5 primeiras linhas (solicitada):**

```
Feature              | Intelligence            | Site                   | Decisão         | Justificativa
Upload PDF ABF       | /backoffice/upload      | —                      | MIGRA INTEGRAL  | Entrada crítica de dados ABF
Relatórios ABF       | /backoffice/relatorios  | —                      | MIGRA INTEGRAL  | Decorrência do upload
Central de Fontes    | /backoffice/fontes      | —                      | MIGRA ADAPTADO  | Redesenhar usando MacroSyncLog
Dashboard de Dados   | /backoffice/dashboard-* | parcial em /mercado    | MIGRA ADAPTADO  | Versão admin; queries SQLite→PG
Franquias (admin)    | /backoffice/franquias   | /admin/franquias       | MIGRA + MERGE   | Dedupe 1.387 raspadas vs CRUD atual
```

---

## Seção 4 — Dívidas técnicas no site

### 4.1 Código

**Backend NestJS legado em `api/` ainda vivo:**
- Dir completo com `src/`, `prisma/`, `docker-compose.yml`, `Dockerfile`.
- Git mostra 3 arquivos modificados em `api/src/users/` (commits recentes).
- FastAPI em `deploy/ec2/app/` é o backend de produção desde a Sessão 3-4.
- **Ação:** decommissionar NestJS depois da fusão — não misturar com a fusão em si.

**Dois dumps SQL commitados/untracked no repo:**
- `api/dump-dados-20260408.sql` (3,0 MB)
- `api/dump-dados-20260413.sql` (3,3 MB)
- **Ação:** mover pra fora do repo ou gitignore. Provavelmente acidentalmente versionados. 6,3 MB desnecessários.

**Scrapers JS soltos na raiz (untracked):**
- `scraper-logos-favicon.js`, `scraper-logos-html.js`, `scraper-mindconsulting.js`
- `scraper-progress.json` (3,1 MB de progresso — arquivo enorme, atualizado em 15/04/2026)
- Sem CLAUDE.md descrevendo quem invoca; não há cron visível no repo.
- **Ação:** (a) decidir se são ativos e, se sim, mover pra `scripts/scrapers/` com docs ou (b) deletar. Progress file deve ir pro gitignore de qualquer forma.

**Frontend modificado não-commitado:**
- ~36 arquivos em `web/src/` modificados (admin layout, header, home sections, quiz, login).
- Risco: se essas mudanças esbarrarem em áreas que a fusão vai tocar, vai dar merge pain.
- **Ação:** commitar ou stashar essas mudanças ANTES de começar a fusão. Não dá pra fundir em cima de 36 arquivos sujos.

**Env var não-usada:**
- `.env` tem `GROQ_API_KEY=` vazio. Feature removida (commit `refactor: remove LLM/Groq module` histórico). Limpeza cosmética.

### 4.2 Tabelas/rotas candidatas a drop (apenas quando essas fases acontecerem)

| Alvo | Where | Condição pra drop |
|---|---|---|
| `RankingBugnumber` (tabela + router + `/admin/big-numbers` + queries frontend) | `app/models.py:823`, `app/routers/big_numbers.py`, `web/src/queries/{rankingBigNumbers,ranking-big-numbers}.ts`, `web/src/app/(admin)/admin/big-numbers/` | Sua decisão — drop total (Seção 6 detalha passos) |
| `AbfSegmentEntry` | `app/models.py:858`, `app/routers/abf_segments.py`, 6 arquivos frontend | ⚠️ **CONFIRMAR PRIMEIRO** — está wired em NestJS + FastAPI + 6 arquivos frontend. Se drop, é grande |
| `audit_log` (SQLite no Intelligence) | `api/abf.db` | Morre junto com o SQLite ao final da fusão — não migrar |
| Backend NestJS inteiro (`api/`) | `api/**` | Decommissionar após fusão completa |

### 4.3 Imports quebrados a esperar

Quando dropar `RankingBugnumber`:
- `app/main.py` (remove mount do router)
- Dashboard `/admin` consome `/ranking-big-numbers` → remover ou trocar pela query nova
- `web/src/queries/rankingBigNumbers.ts` + `web/src/queries/ranking-big-numbers.ts` (❓ **dois arquivos, possível duplicação**)
- NestJS legado tem `api/src/modules/ranking-big-numbers/` com controller+service+module

Quando migrar **franquias**:
- Intelligence's 1.387 registros vs site's `Franchise` — conflito potencial em `slug` (único). Estratégia de merge precisa de sessão dedicada.

---

## Seção 5 — Ordem proposta de migração

Sua sugestão inicial — Fontes → Upload PDF → Relatórios → Dashboard → resto — está basicamente certa. Ajustes:

### Fase 0 — Higiene pré-fusão (1 sessão)

Antes de qualquer migração:

1. Commitar ou stashar os 36 arquivos modificados em `web/src/`.
2. Mover os 2 dumps SQL + 3 scrapers + progress.json pra fora do repo (ou gitignore).
3. Remover `GROQ_API_KEY=` vazio do `.env` e `.env.example`.
4. **Decisão AbfSegmentEntry**: confirma drop ou mantém (impacta se vai migrar o dashboard admin ABF do Intelligence).
5. Garantir que o macro sync systemd rodou ao menos 1x com sucesso (validação da infra).

### Fase 1 — Backbone de dados ABF (2 sessões)

1. **Central de Fontes** (sessão curta, read-only): porta `/backoffice/fontes` → `/admin/fontes`. Zero risco, só consome `MacroSyncLog` + contagens das tabelas macro já migradas. Valida que o wiring Intelligence→Site funciona.
2. **Upload PDF + Relatórios ABF**: traz Claude API + pdfplumber + ANTHROPIC_API_KEY. Escreve em `AbfReport`/`AbfRevenue`/`AbfIndicator` já existentes. Testar com 1 PDF real antes de ir adiante.

### Fase 2 — Consumo (2 sessões)

3. **Dashboard de Dados** (admin view): as 5 abas apontando pro PG. Gráficos Recharts já estão no stack do site.
4. **Logs/Sistema unificado**: consolida `/backoffice/{logs,sistema,auditoria}` em `/admin/logs`. Descarta `audit_log` do Intelligence.

### Fase 3 — Conteúdo gerado por IA (3+ sessões, maior risco)

5. **Editorial de notícias** (merge com News existente): precisa alinhar schemas `noticias_fila`/`noticias_publicadas` ↔ `News`. Semântica de status + versionamento de título.
6. **Studio — cards Instagram**: geração de copy + template. Imagem depende de infra de render (Pillow).
7. **Studio — carrosséis**: 5 tipos, cada um com lógica própria. Última fase por complexidade.

### Fase 4 — Franquias (2+ sessões, MAIOR risco)

8. **Franquias — dedupe e merge**: 1.387 raspadas × 1.409 no site. Site manda (Decisão 2 da Seção 0); Intelligence só contribui franquias NOVAS. Execução em duas sessões: (a) diff report read-only, humano revisa; (b) UPSERT só do bucket NEW + revisão manual do FUZZY.

#### Regra de match (Decisão 2)

Normalização — usar a MESMA função em ambos os lados da comparação:

```python
import unicodedata, re

def normalize_name(s: str) -> str:
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode()
    s = re.sub(r'[^\w\s]', '', s.lower())
    return re.sub(r'\s+', ' ', s).strip()
```

Sequência de match (para cada franquia do Intelligence, tentar nesta ordem):

1. **Match exato por `slug`** → se bater, é `EXACT_MATCH`.
2. **Match exato por `normalize_name(nome)`** → se bater, também `EXACT_MATCH`.
3. **Match fuzzy por `normalize_name`** com Levenshtein ≤ 2 → `FUZZY_MATCH`.
4. Caso contrário → `NEW`.

Output da Fase 4a — diff report com 3 buckets:

| Bucket | Ação | Volume esperado |
|---|---|---|
| `EXACT_MATCH` | **Skip** — site já tem, nada muda. | ~1.300 |
| `FUZZY_MATCH` | Revisão humana 1-a-1 no report (CSV ou tela dedicada). | ~20–80 |
| `NEW` | Insert em `Franchise` via UPSERT por slug (sem sobrescrever campos existentes). | ~50–100 |

Fase 4b só executa depois do humano triar os `FUZZY_MATCH`.

### Fase 4.5 — Reconstruir `/mercado` em cima de `AbfRevenue` + `SegmentAcronym` (1 sessão)

**Pré-requisito pra Fase 5.** `/mercado` público hoje lê de `AbfSegmentEntry`. A Decisão 1 (Seção 0) manda dropar essa tabela, então precisamos trocar a fonte de dados da página **antes** do drop — senão o site público quebra em produção.

Tarefas:

1. Mapear todos os pontos em `web/src/**/` e `deploy/ec2/app/routers/abf_segments.py` que servem dados pro `/mercado`.
2. Reescrever as queries em cima de `AbfRevenue` (série de faturamento) + `SegmentAcronym` (mapa segmento→sigla) — ambas já populadas e com siglas corrigidas.
3. Deploy do `/mercado` novo, smoke test em produção com dados reais.
4. Só então libera Fase 5 pra dropar `AbfSegmentEntry`.

### Fase 5 — Limpeza (1 sessão)

9. Deletar `AbfSegmentEntry` inteiro: tabela PG + router `abf_segments.py` + mount em `main.py` + 6 arquivos frontend sob `web/src/**/abfSegments/**` + painel `/admin/segmentos-abf` + controller NestJS legado. Só rodar APÓS Fase 4.5 estar em produção.
10. Deletar `/admin/big-numbers` + `RankingBugnumber` (sua instrução original).
11. Decommissionar NestJS legado (`git rm -r api/`, remover `docker-compose*.yml` se só atendiam NestJS).
12. Revogar/remover Intelligence (após confirmar que nada mais depende).

**Ajuste da sua ordem sugerida:** troquei "Fontes primeiro" pra manter a ordem (Fontes é mais seguro que Upload pra começar), mas inserei Fase 0 (higiene) antes de tudo — os 36 arquivos sujos + dumps são um risco de merge caos se você começar a fusão antes.

---

## Seção 6 — Checklist de limpeza pós-fusão

### Ao final da Fase 1 (Backbone)

- [ ] Remover routers órfãos do Intelligence que viraram dead code no fork de migração
- [ ] Verificar que `/api/fontes/*` do Intelligence não está sendo chamado em produção
- [ ] Se `AbfSegmentEntry` for dropado, remover: router `abf_segments.py`, mount em `main.py`, 6 arquivos frontend sob `web/src/**/abfSegments/**`, import em `app/models.py`, controller NestJS legado

### Ao final da Fase 3 (Conteúdo IA)

- [ ] Deletar tabelas SQLite do Intelligence uma vez migradas: `noticias_raw`, `noticias_fila`, `noticias_publicadas`, `posts_instagram`, `carrosseis_instagram`
- [ ] Verificar que `pdfplumber`, `Pillow`, `matplotlib` estão em `deploy/ec2/requirements.txt` (não só no Intelligence)
- [ ] Padronizar cliente Claude: migrar do `requests` cru pro SDK oficial `anthropic` se for trazer junto
- [ ] Remover dependência de `Claude API` do Intelligence (uma vez não chamado)

### Ao final da Fase 4 (Franquias)

- [ ] Reconciliar: qualquer franquia raspada que não entrou no site precisa ter uma razão documentada
- [ ] Remover tabela `franquias` do SQLite
- [ ] Deletar `/api/franquias/*` do Intelligence

### Ao final da Fase 5 (Cleanup geral)

- [ ] Drop `RankingBugnumber` PG table + index + todos os arquivos listados na Seção 4.3
- [ ] Decommissionar backend NestJS: `git rm -r api/` (após garantir que nada no frontend aponta pro NestJS)
- [ ] Remover `docker-compose.yml` / `docker-compose.prod.yml` se eram só pro NestJS
- [ ] Arquivar Intelligence: `git archive` ou `mv ~/Developer/mercadofranquia ~/Developer/_archived/`
- [ ] Limpar deps npm não usadas: `next-auth` (se não rolou pro site), Recharts (se já existia), `@tanstack/react-table`
- [ ] Limpar deps pip não usadas: `requests` (se Anthropic SDK assumiu), `matplotlib` (se charts são só Recharts agora)
- [ ] Gerar novo `FUSAO_CHANGELOG.md` documentando o que ficou de onde

---

## Descobertas que merecem atenção

1. **`AbfSegmentEntry` não é drop candidate óbvio.** Você mencionou na spec ("Tabelas PG que serão dropadas depois (AbfSegmentEntry, RankingBugnumber)"). Grep mostra: usado em `app/models.py`, `app/routers/abf_segments.py`, NestJS em `api/src/modules/abf-segments/`, 6 arquivos frontend (`web/src/services/abfSegments.ts`, schema, hook `useAbfSegments.ts`, 3 componentes em `web/src/components/admin/panels/abfSegments/`). Decidir manter vs deletar **antes** da fusão — impacta se `/admin/segmentos-abf` fica ou some.

2. **`RankingBugnumber` — grafia inconsistente.** A tabela está grafada `Bugnumber` (erro?) e não `BigNumber`. Frontend tem DOIS arquivos de query (`rankingBigNumbers.ts` + `ranking-big-numbers.ts`) — provável duplicação. Se vamos deletar, deletamos ambos.

3. **Intelligence usa Claude via HTTP cru, não SDK oficial.** Modelo `claude-sonnet-4-20250514`. Na migração vale padronizar pro `anthropic` oficial — melhor caching, error handling, observabilidade. Precisa de `ANTHROPIC_API_KEY` no EC2 (não existe hoje).

4. **Funil editorial praticamente vazio.** 161 `noticias_raw` → 29 `noticias_fila` → **só 2 `noticias_publicadas`**. O pipeline Intelligence está funcional mas pouco usado. Validar se vale migrar o workflow completo ou simplificar.

5. **`audit_log` do Intelligence: 0 linhas.** Schema existe mas nunca foi escrito. A tela `/backoffice/auditoria` + endpoint `/api/audit` são casca. Descartar explicitamente, não migrar.

6. **Backend NestJS no site tem commits recentes.** Apesar do FastAPI ser produção, 3 arquivos em `api/src/users/` foram modificados recentemente. Alguém (você?) ainda mexe nele. Confirmar se dá pra congelar antes da fusão.

7. **1.387 franquias no Intelligence vs Franchise do site.** Data reconciliation é a sessão mais perigosa. Precisa estratégia:
   - Match por `slug`? (colisões possíveis)
   - Match por CNPJ? (Intelligence coleta CNPJ?)
   - Match fuzzy por nome?
   - Site's Franchise tem 50+ colunas — Intelligence's franquias tem ~20. Colunas divergentes precisam mapeamento explícito.
   - Dedicar uma sessão SÓ pra diff report antes de executar.

8. **Intelligence tem um `backend/` NestJS separado (`api/` é FastAPI).** Confusão potencial: ambos projetos têm um "api" FastAPI E um "backend/api" NestJS. No Intelligence o `backend/` usa Groq e está órfão (frontend não chama). Zero impacto na fusão, só vale saber que existe.

9. **`carrosseis_instagram.slides_json`** é campo TEXT com JSON. Scripts Pillow renderizam PNG a partir desse JSON. Migração pro PG pode usar JSONB nativo + preservar a renderização.

10. **Intelligence é single-user sem gestão de usuários.** NextAuth com credenciais hardcoded em env. Ao migrar pro site, tudo vira acessível só pra `role=ADMIN` já existente — facilita, não dificulta.

---

## Seção 8 — Apêndice A — Fase 0 passo a passo

Instruções concretas. Rodar da raiz do repo `~/Developer/mercadofranquia-site/` salvo indicação explícita.

### §4.1 — Congelar NestJS

```bash
# 1. Commitar qualquer coisa pendente em api/ ou descartar
git status api/
# 2. Criar commit de freeze com nota ao topo do README
cat >> api/README.md <<'EOF'

## ⛔ CONGELADO DESDE 2026-04-18

Este backend NestJS está **congelado**. Todo código novo vai para
`deploy/ec2/app/` (FastAPI em produção no EC2). Decommissionamento
programado para a Fase 5 da fusão — ver `docs/FUSAO_INVENTORY.md`.

Não aceitar PRs ou commits contra `api/` sem revisão explícita.
EOF

git add api/README.md
git commit -m "chore(api): freeze NestJS — trabalho novo vai pro FastAPI em deploy/ec2/"
```

### §4.2 — Limpar os 2 dumps SQL

```bash
git rm api/dump-dados-20260408.sql api/dump-dados-20260413.sql

# Adicionar ao .gitignore (pattern genérico)
grep -qxF 'api/dump-*.sql' .gitignore || echo 'api/dump-*.sql' >> .gitignore

git add .gitignore
git commit -m "chore: remove dumps SQL versionados (~6.3 MB) + ignore pattern"
```

### §4.3 — Tratar os 3 scrapers JS soltos

**Triar antes de mover.** Perguntas a responder:

- `scraper-logos-favicon.js` — ainda uso pra backfill de logos?
- `scraper-logos-html.js` — ainda uso como fallback?
- `scraper-mindconsulting.js` — API Mind Consulting ainda é fonte ativa?

Decisão por arquivo:

```bash
# SE ATIVO — mover pra scripts/scrapers/ com README
mkdir -p scripts/scrapers
git mv scraper-logos-favicon.js scripts/scrapers/
# (etc — repetir pra cada que continua ativo)
cat > scripts/scrapers/README.md <<'EOF'
# Scrapers auxiliares

Scripts JS de backfill/sync rodados sob demanda (não cron automatizado).

- `scraper-logos-favicon.js` — backfill logos via og:image + Google Favicon API
- `scraper-logos-html.js` — fallback por scraping HTML
- `scraper-mindconsulting.js` — sync legado da API Mind Consulting

Invocação: `node scripts/scrapers/<nome>.js`. Progresso persistido em
`scraper-progress.json` (gitignored).
EOF

# SE INATIVO — arquivar
mkdir -p deploy/_archived/scrapers
git mv scraper-mindconsulting.js deploy/_archived/scrapers/   # exemplo
# (repetir pra cada inativo)

# De qualquer forma — ignorar o arquivo de progresso
grep -qxF 'scraper-progress.json' .gitignore || echo 'scraper-progress.json' >> .gitignore

git add .gitignore scripts/ deploy/ 2>/dev/null
git commit -m "chore: organiza scrapers JS soltos (ativo → scripts/scrapers, inativo → archived)"
```

### §4.4 — Remover `GROQ_API_KEY` vazio

```bash
# .env (não é versionado, mas limpa mesmo assim)
sed -i.bak '/^GROQ_API_KEY=/d' .env && rm .env.bak

# .env.example é versionado
sed -i.bak '/^GROQ_API_KEY=/d' .env.example && rm .env.example.bak

git add .env.example
git commit -m "chore: remove GROQ_API_KEY não usada (feature removida há meses)"
```

### §4.5 — 36 arquivos frontend modificados — triar caso a caso

```bash
# Listar o que está sujo antes de decidir
git status --porcelain | awk '$1 ~ /^(M|A)/ && $2 ~ /^web\/src\// { print $2 }'

# Abrir o diff agrupado por área lógica e decidir
git diff --stat web/src/app/\(admin\)/         # admin
git diff --stat web/src/app/\(public\)/        # home/hero/sections
git diff --stat web/src/app/\(franchisor\)/    # portal franqueador
git diff --stat web/src/components/            # componentes compartilhados
```

Para cada grupo, decidir:

- **Commitar** se a mudança é intencional e não conflita com o plano de fusão.
- **Stashar nomeado** (`git stash push -m 'pre-fusao: <descricao>' -- <paths>`) se valiosa mas vai tocar os mesmos arquivos da fusão.
- **Descartar** (`git checkout -- <path>`) se é experimento/lixo.

⚠️ **Não começar Fase 1 com `web/src/` sujo.** Qualquer caminho que a fusão vai editar precisa estar limpo.

### §4.6 — Preparar `ANTHROPIC_API_KEY` no EC2

Não precisa valor real agora — só deixar o slot pronto. No EC2:

```bash
# Editar /etc/systemd/system/mf-api.service e adicionar:
#   Environment=ANTHROPIC_API_KEY=<valor-real-na-fase-1.2>
#
# Placeholder pra não esquecer:
#   Environment=ANTHROPIC_API_KEY=__TODO_FASE_1_2__
#
# Equivalente no mf-macro-sync.service (se o sync for acabar chamando Claude).
```

No momento da Fase 1.2 (Upload PDF):

- Gerar key em console.anthropic.com
- `sudo systemctl edit mf-api.service` → definir valor real
- `sudo systemctl daemon-reload && sudo systemctl restart mf-api`
- Validar disponibilidade do modelo `claude-sonnet-4-5-20250929` (pode ter sucessor em 2026-04)

### §4.7 — Smoke test do timer macro-sync

Antes de começar a Fase 1, confirmar que o pipeline de macro já está rodando em produção (Sessões 3–5):

```bash
# No EC2
systemctl list-timers mf-macro-sync.timer
systemctl status mf-macro-sync.service

# Último log
journalctl -u mf-macro-sync.service -n 200 --no-pager | tail -50

# Verificar que MacroSyncLog tem entradas status='ok' recentes
psql -U mf_user -d mercadofranquia -c \
  'SELECT fonte, status, "registrosInseridos", "duracaoMs", "createdAt"
   FROM "MacroSyncLog"
   ORDER BY "createdAt" DESC LIMIT 20;'
```

**Critério de sucesso:** pelo menos 1 execução completa com status `ok` nas últimas 24h em todas as 4 fontes (BCB macro, IBGE, PMC, CAGED). Se alguma estiver `erro`, investigar antes de começar a fusão — não empilhar novos problemas em cima de infra quebrada.

---

**Este doc é a fonte de verdade durante a fusão.** Toda sessão começa conferindo: qual fase, o que já foi feito, o que esse doc diz sobre a próxima etapa. Atualize-o (ou o CHANGELOG que mencionei) a cada sessão concluída.
