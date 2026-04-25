# Redesign — Editor de Franquia + Landing Pública

**Data da spec:** 25 de abril de 2026
**Autor:** Breno Moretti (decisões) + Claude (estruturação)
**Sessão original:** `/mnt/transcripts/2026-04-25-14-12-36-mf-fatia4-pr2b-redesign-editor.txt`

---

## Resumo executivo

Reformulação de duas páginas do mercadofranquia:

1. **Editor de franquia** (`/franqueador/franquias/[slug]/editar`) — onde o franqueador cadastra/edita os dados da marca.
2. **Página pública de venda** (`/franquias/[slug]`) — onde o investidor avalia a marca e vira lead.

Objetivo: transformar a página pública de **perfil de catálogo** em **landing de venda**, e expandir o editor pra coletar todos os dados necessários pra essa nova landing.

Premissa crítica: **não quebrar franquias já cadastradas**. Todos os campos novos são opcionais; a renderização da pública é progressiva (blocos sem dados não aparecem).

---

## 1. Estado atual vs proposto

### Editor hoje
- 4 tabs: Informações gerais, Investimento, Mídia, Modelos de negócio
- Banner "Não aprovada" sem CTA, sem motivo
- Sem indicador de progresso
- Sem botão Salvar visível
- Descrição dividida em "curta" (1000 chars) e "detalhada" (10000 chars)

### Editor proposto
- **3 tabs**: Informações | Negócio & investimento | Mídia & contato
- Banner adaptativo (3 estados: Em análise, Não aprovada com motivo+ações, Aprovada com link pública)
- Indicador de progresso ("X% · Y de Z obrigatórios" + lista do que falta)
- Botão Salvar fixo no topo + auto-save com indicator
- Descrição única
- Subsegment removido do editor (mantido no DB)

### Pública hoje (presumida — site atual)
- Cards genéricos de catálogo
- Foco em listagem, não em conversão

### Pública proposta
- Banner full-width
- Hero com logo + tagline + métricas-pill + CTA principal
- Cards de modelos (lado a lado quando 1+ modelos)
- Bloco "Em breve — Ferramentas pro investidor decidir" (placeholder pros 4 serviços do roadmap)
- Sobre a marca
- Vídeo institucional (bloco dedicado)
- Como funciona (stepper de etapas)
- Diferenciais (bullets)
- Perfil do franqueado ideal
- Galeria
- Depoimentos
- Form de lead com **capital disponível** (crítico pra qualificar)
- Footer (canais de contato — controlados por plano)

---

## 2. Decisões consolidadas

### 2.1 Estrutura de tabs

| Decisão | Razão |
|---|---|
| Mesclar Investimento + Modelos numa tab única "Negócio & investimento" | Multi-modelo será comum (food truck + loja + quiosque). Mental model único, source of truth sem ambiguidade. Hick's law: menos tabs = menos decisão. |
| Manter "Mídia" como tab separada (renomeada "Mídia & contato") | Acomoda upload de assets + canais de contato sem inflar a tab principal |

### 2.2 Tab "Negócio & investimento" — lógica adaptativa

**Sem modelos cadastrados (estado atual de todas as franquias):**
- Campos diretos (investimento, payback, faturamento, royalties, taxas, capital giro, área)
- Compatibilidade total com franquias legadas

**Com 1+ modelos cadastrados:**
- Cada modelo tem seus próprios números (investimento, payback, faturamento, área, capital giro, taxa franquia)
- Royalties + propaganda continuam globais (válidos pra todos os modelos)
- Resumo agregado calculado automaticamente (range mín-máx)
- Pública mostra cards lado a lado

**Banner explicativo no topo** (versão aprovada — foco em valor):
> **Mostre que sua franquia se adapta**
>
> Cada investidor tem um capital diferente. Cadastrando seus modelos (loja, quiosque, container...), sua página pública apresenta **cards lado a lado** — o investidor compara opções na hora e encontra a que cabe no bolso dele.

### 2.3 Frescor de unidades (regra escalada)

Dado de unidades fica desatualizado rápido e prejudica credibilidade. Mecanismo:

| Dias desde última atualização | Status | Ação |
|---|---|---|
| 0–29 | 🟢 Fresco | "Confirmado há X dias" abaixo do input |
| 30–44 | 🟡 Cobrando | Banner discreto no editor + botão "Sim, confirmar" |
| 45–59 | 🟠 Cobrando forte | Toast no painel ao logar + email mensal |
| 60+ | 🔴 Desatualizado | Badge "⚠ Dado pode estar desatualizado" **na página pública** |

**Botão "Confirmar (sem mudar)"** é crítico — atualiza `lastConfirmedAt` sem forçar mudança artificial do número.

**Escopo:** apenas `totalUnits` por enquanto. Outros campos financeiros mudam pouco (anual), escalar depois se validar.

### 2.4 Canais de contato — modelo Free/Premium

**Sempre coletados no editor**, mas exibição na pública depende do plano:

| Canal | Free | Premium |
|---|---|---|
| Site oficial | ✅ | ✅ |
| Telefone | 🔒 | ✅ |
| WhatsApp | 🔒 | ✅ |
| Email comercial | 🔒 | ✅ |
| Instagram | 🔒 | ✅ |
| Facebook | 🔒 | ✅ |
| LinkedIn | 🔒 | ✅ |
| Form de lead | ✅ (canal exclusivo) | ✅ |

**Modelagem do plano adiada.** Decisão de campo `plan` simples vs tabela `Subscription` separada será feita quando o primeiro pagante chegar.

### 2.5 Serviços ao investidor (roadmap futuro)

Reservar **espaço visual na pública** entre "Modelos" e "Sobre", como bloco "Em breve":

- Simulação de crédito (financeiro)
- Triagem de praça (análise de ponto)
- Mapa de concorrentes (PostGIS + Receita Federal)
- Checklist COF (Circular de Oferta de Franquia)

Diferencia mercadofranquia de portais simples (Portal ABF, EncontreSuaFranquia) que só listam.

**Não construir agora** — só desenhar o espaço pra quando os serviços virarem realidade.

### 2.6 Mudanças textuais

- Subsegment removido do editor (campo continua no DB)
- "Descrição curta" + "Descrição detalhada" → 1 campo único "Descrição"
- Banner "Não aprovada" antigo ("Entre em contato com a equipe") → banner adaptativo com motivo + 2 botões ("Reenviar pra análise" + "Falar com a equipe")
- Chat do Hubspot integrado em páginas logadas (substituindo "Entre em contato" textual)

### 2.7 Melhorias UX aprovadas (lista #1-11 da rodada)

1. Campos obrigatórios visíveis (checklist no topo)
2. Auto-save com debounce 2s + indicator
3. Estado acionável (REJECTED com motivo + botões)
4. Preview público (botão "Ver como aparecerá")
5. Helpers contextuais (placeholders informativos)
6. Validação inline com mensagens úteis
7. Hierarquia visual com seções colapsáveis
8. Pergunta-resposta em vez de label
9. Drag-and-drop pros uploads
10. Atalhos de teclado (Cmd+S salva)
11. Onboarding guiado pro primeiro cadastro

**Descartados:** templates por segmento (#12), exemplos visuais (#13), edição colaborativa (#14).

---

## 3. Mudanças no banco de dados

### 3.1 Estado atual da tabela `Franchise` (campos relevantes)

Já existem (vão ser **reusados**, sem migration):
```
name, slug, segment, subsegment, businessType
description, detailedDescription, logoUrl, thumbnailUrl, videoUrl, galleryUrls
minimumInvestment, maximumInvestment, franchiseFee, averageMonthlyRevenue
royalties, advertisingFee, calculationBaseRoyaltie, calculationBaseAdFee
setupCapital, workingCapital, storeArea
minimumReturnOnInvestment, maximumReturnOnInvestment
totalUnits, totalUnitsInBrazil, unitsEvolution
franchiseStartYear, brandFoundationYear, abfSince
headquarter, headquarterState, isAbfAssociated, scrapedWebsite
```

### 3.2 Campos novos (1 migration agregada)

**Tab Informações:**
```python
tagline: Mapped[str | None] = mapped_column(String(200), nullable=True)
differentials: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
ideal_franchisee_profile: Mapped[str | None] = mapped_column(Text, nullable=True)
process_steps: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
# Estrutura: [{"title": str, "description": str}, ...]
testimonials: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
# Estrutura: [{"name": str, "role": str, "photoUrl": str | None, "quote": str}, ...]
```

**Tab Mídia & contato:**
```python
banner_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
# Separado de thumbnailUrl. Banner = hero da pública (1920x600). Thumbnail = card de listagem.

phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)
public_email: Mapped[str | None] = mapped_column(String(100), nullable=True)
instagram_url: Mapped[str | None] = mapped_column(String(200), nullable=True)
facebook_url: Mapped[str | None] = mapped_column(String(200), nullable=True)
linkedin_url: Mapped[str | None] = mapped_column(String(200), nullable=True)
```

**Frescor de unidades:**
```python
total_units_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
total_units_last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

### 3.3 Total de campos novos

13 colunas nullable. Zero risco de quebrar dados existentes (todos os defaults são `NULL`).

### 3.4 Campos que ficam ocultos no editor (mas continuam no DB)

- `subsegment` — decisão de UX, não técnica. Continua aceitando valor via API pra retro-compat.
- `detailedDescription` — vai ser fundido com `description` no frontend. Backend continua aceitando até migration de dados rodar (tarefa separada, opcional).

---

## 4. Mudanças no frontend

### 4.1 Estrutura de páginas

**Editor:**
- `web/src/app/(franchisor)/franqueador/franquias/[slug]/editar/page.tsx` — entry
- `web/src/components/franqueadores/editor/EditorHeader.tsx` — header + status banner
- `web/src/components/franqueadores/editor/ProgressBar.tsx` — indicador de progresso
- `web/src/components/franqueadores/editor/Tabs/TabInfo.tsx` — Tab Informações
- `web/src/components/franqueadores/editor/Tabs/TabBusiness.tsx` — Tab Negócio & investimento
- `web/src/components/franqueadores/editor/Tabs/TabMedia.tsx` — Tab Mídia & contato

**Pública:**
- `web/src/app/franquias/[slug]/page.tsx` — entry
- `web/src/components/franquias/public/Banner.tsx`
- `web/src/components/franquias/public/Hero.tsx`
- `web/src/components/franquias/public/ModelsCards.tsx`
- `web/src/components/franquias/public/ServicesPlaceholder.tsx`
- `web/src/components/franquias/public/AboutBlock.tsx`
- `web/src/components/franquias/public/VideoBlock.tsx`
- `web/src/components/franquias/public/ProcessStepper.tsx`
- `web/src/components/franquias/public/Differentials.tsx`
- `web/src/components/franquias/public/IdealProfile.tsx`
- `web/src/components/franquias/public/Gallery.tsx`
- `web/src/components/franquias/public/Testimonials.tsx`
- `web/src/components/franquias/public/LeadForm.tsx`
- `web/src/components/franquias/public/ContactFooter.tsx`

### 4.2 Renderização condicional na pública

```tsx
// Cada bloco verifica se há dados antes de renderizar
{franchise.tagline && <p className="hero-tagline">{franchise.tagline}</p>}
{franchise.bannerUrl && <Banner url={franchise.bannerUrl} />}
{franchise.businessModels?.length > 0
  ? <ModelsCards models={franchise.businessModels} />
  : <DirectInvestmentSummary franchise={franchise} />}
{franchise.processSteps?.length > 0 && <ProcessStepper steps={franchise.processSteps} />}
{franchise.differentials?.length > 0 && <Differentials items={franchise.differentials} />}
{franchise.idealFranchiseeProfile && <IdealProfile text={franchise.idealFranchiseeProfile} />}
{franchise.galleryUrls?.length > 0 && <Gallery urls={franchise.galleryUrls} />}
{franchise.videoUrl && <VideoBlock url={franchise.videoUrl} />}
{franchise.testimonials?.length > 0 && <Testimonials items={franchise.testimonials} />}
```

Resultado: franquia legada (sem nada novo preenchido) renderiza só os blocos básicos. Conforme franqueador completa o cadastro, mais blocos aparecem progressivamente.

### 4.3 Lógica do plano Free/Premium na pública

```tsx
const isPaid = franchise.plan === 'PREMIUM' // ou via Subscription model no futuro

<ContactFooter>
  {franchise.scrapedWebsite && <Link href={franchise.scrapedWebsite}>Site oficial</Link>}
  {isPaid && franchise.phone && <PhoneBlock phone={franchise.phone} />}
  {isPaid && franchise.whatsapp && <WhatsappBlock />}
  {/* etc */}
</ContactFooter>
```

Form de lead aparece sempre, em todos os planos.

### 4.4 Frescor de unidades

```tsx
// No editor
const daysSince = (date: Date) => Math.floor((Date.now() - date.getTime()) / 86400000)
const lastUpdate = max(franchise.totalUnitsUpdatedAt, franchise.totalUnitsLastConfirmedAt)
const days = daysSince(lastUpdate)

if (days >= 30 && days < 45) <BannerEditor>Faz {days} dias. Ainda são {franchise.totalUnits}?</BannerEditor>
if (days >= 45) <Toast>Confirme as unidades</Toast>
// Email automatizado disparado em D+45 (cron job)

// Na pública
{days >= 60 && <Badge>⚠ Dado pode estar desatualizado</Badge>}
```

### 4.5 Auto-save

```tsx
const debouncedSave = useDebouncedCallback((data) => {
  saveFranchise(data).then(() => setSaveIndicator('Salvo agora'))
}, 2000)

useEffect(() => {
  setSaveIndicator('Salvando...')
  debouncedSave(formData)
}, [formData])
```

---

## 5. Mudanças no backend

### 5.1 Endpoints novos

```
POST /franchises/me/confirm-units
  - Atualiza total_units_last_confirmed_at = NOW()
  - Não muda total_units
  - Auth: dono da franquia

GET /franchises/me/freshness
  - Retorna { totalUnits: { updatedAt, lastConfirmedAt, daysSinceLastUpdate, status } }
  - Usado pelo banner do editor
```

### 5.2 Endpoints modificados

```
PUT /franchises/me
  - Quando total_units muda, atualiza total_units_updated_at = NOW()
  - Resto do payload aceita os 13 campos novos
```

### 5.3 Tarefas agendadas

```
# Cron diário — disparar emails de cobrança
def send_unit_freshness_emails():
    franchises = query.filter(
        days_since_freshness >= 45 AND days_since_freshness < 46
    )
    for f in franchises:
        ses.send(f.owner.email, template="unit_freshness_reminder")
```

---

## 6. Plano de execução

### 6.1 Fatias propostas

A spec é grande. Sugestão de fatiamento:

**Fatia 1 — Estrutura do editor (1 PR)**
- Reduzir 4 tabs pra 3 (mesclar Investimento + Modelos)
- Banner adaptativo (3 estados)
- Indicador de progresso
- Botão Salvar visível + auto-save
- Subsegment oculto no UI
- Descrição unificada (1 campo no UI, backend continua aceitando ambos)

**Fatia 2 — Campos novos da Tab Informações (1 PR)**
- Migration: tagline, differentials, ideal_franchisee_profile, process_steps, testimonials
- UI dos novos campos no editor
- Renderização na pública (todos com condicional)

**Fatia 3 — Campos novos da Tab Mídia & contato (1 PR)**
- Migration: banner_url, phone, whatsapp, public_email, instagram_url, facebook_url, linkedin_url
- UI dos novos campos no editor
- Hero da pública usa banner_url
- ContactFooter na pública (lógica de plano fica genérica até modelagem real)

**Fatia 4 — Frescor de unidades (1 PR)**
- Migration: total_units_updated_at, total_units_last_confirmed_at
- Endpoint POST /franchises/me/confirm-units
- Banner no editor + badge na pública
- Cron job pra email D+45

**Fatia 5 — Refinamentos UX (1 PR)**
- Helpers contextuais, validação inline, drag-drop, atalhos teclado
- Preview público (modal)
- Onboarding tour primeiro acesso

### 6.2 Backend mínimo viável (Fatia 0 implícita)

Antes da Fatia 1, fazer 1 migration agregada com TODOS os 13 campos novos como nullable. Razão: rodar migration única evita 4 deploys de DB. Frontend ainda não usa, mas backend já aceita via PUT /franchises/me.

### 6.3 Compatibilidade backward

Cada fatia é independente. Se Fatia 2 atrasa, Fatia 1 já está em prod e funciona. Pública renderiza só os blocos com dados.

---

## 7. Backlog não incluído (decisões futuras)

### Estratégico (memória #18)
- Conversão: CTA sticky, captura progressiva de lead, quiz de matching investidor↔franquia
- Confiança: selo ABF Verified, ranges Bloomberg-style, comparação com média do segmento, preview público side-by-side
- SEO: meta tags dinâmicos, SSG/ISR
- Operação: timeline de aprovações, dashboard de views, notificações in-app
- Mobile: drawer/bottom-sheet em vez de tabs, upload via WhatsApp
- Pós-aprovação: FAQ editável, integração agenda

### Roadmap plataforma (memória #19)
- Simulação de crédito
- Triagem de praça (análise de ponto)
- Mapa de concorrentes (PostGIS + Receita Federal)
- Checklist COF

### Modelagem futura
- Plano Free/Premium (campo simples vs tabela Subscription) — decidir quando primeiro pagante chegar
- Subsegment — decidir se vira filtro de catálogo ou se é dropado de vez
- detailedDescription — decidir se migra dados pra description ou mantém duplicado

### Bugs conhecidos
- FranchisorEditing.tsx (admin editar franqueador) crasheia com cnpj/phone null em prod (memória #17)
- Refactor enum FranchisorRequestStatus duplicado (memória #15)

---

## 8. Decisões pendentes pra próxima sessão

1. Modelagem técnica do plano Free/Premium (campo vs tabela)
2. Endpoint específico pra rebuild de progresso/checklist (campos obrigatórios — definir lista exata)
3. Critério exato pra "aprovação" pelo admin (qual conjunto mínimo de campos basta?)
4. Comportamento do badge "atualizado há X dias" — só pra unidades ou expandir pra outros campos?
5. Onboarding tour — quais 4-5 tooltips mostrar no primeiro cadastro?

---

## 9. Mockups visuais gerados na sessão

Renderizados no chat (transcript: `2026-04-25-14-12-36-mf-fatia4-pr2b-redesign-editor.txt`):

1. **editor_franquia_estrutura_v1** — Camada 1 do editor (estrutura, banners adaptativos)
2. **pagina_publica_franquia_v1** — Pública, primeira versão
3. **pagina_publica_franquia_v2_com_banner_video** — Pública v2 com banner full-width + vídeo + bloco de serviços
4. **editor_franquia_expandido_v1** — Tab Informações detalhada
5. **editor_tab_negocio_investimento** — Tab Negócio & investimento (com toggle modos)
6. **editor_tab_midia_contato** — Tab Mídia & contato
7. **editor_tab_negocio_investimento_v2** — Tab Negócio & investimento com explicação aprovada (versão B)

---

## Apêndice — checklist pra Claude Code

Quando for implementar essa spec, fazer nesta ordem:

```
[ ] Ler spec inteira
[ ] Confirmar campos atuais do DB (rodar \d "Franchise" em prod e local)
[ ] Criar migration agregada (Fatia 0 — 13 campos nullable)
[ ] Aplicar migration local + EC2
[ ] Validar PUT /franchises/me aceita os novos campos
[ ] Iniciar Fatia 1 (estrutura editor)
[ ] Cada fatia em PR separada com E2E browser local antes de deploy
[ ] Documentar mudanças nas memórias
```
