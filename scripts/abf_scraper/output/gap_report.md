# Gap Analysis — ABF Scraper × Schema Mercado Franquia

**Total de fichas ABF analisadas:** 191
**Schema versao:** Alembic head 9e73d144e686 (sincronizado prod+local)
**Franchise:** 64 colunas
**BusinessModel:** 19 colunas

---

## 1. Mapeamentos diretos (ABF -> DB, 1:1)

Campos onde tipo e semantica casam. UPSERT pode rodar sem transformacao.

### 1a. ABF top-level -> Franchise

| ABF field | Franchise col | Presenca em ABF | Existe no DB |
|---|---|---|---|
| `slug` | `slug` | 191/191 (100%) | OK |
| `name` | `name` | 191/191 (100%) | OK |
| `scraped_website` | `scrapedWebsite` | 185/191 (96%) | OK |
| `scraped_at` | `lastScrapedAt` | 191/191 (100%) | OK |
| `logo_url` | `logoUrl` | 175/191 (91%) | OK |
| `minimum_investment` | `minimumInvestment` | 185/191 (96%) | OK |
| `maximum_investment` | `maximumInvestment` | 185/191 (96%) | OK |
| `total_units` | `totalUnits` | 184/191 (96%) | OK |
| `headquarter` | `headquarter` | 185/191 (96%) | OK |

### 1b. ABF business_models[] -> BusinessModel

| ABF field | BusinessModel col | Presenca | Existe |
|---|---|---|---|
| `name` | `name` | 236/191 (123%) | OK |

---

## 2. Mapeamentos semanticos (precisam transformacao)

Campos onde dado existe nos 2 lados mas formato/tipagem divergem.

### 2a. Franchise

- **`segment_abf_name`** (191/191) -> `segment`
  - ABF traz nome legivel ('Alimentacao'), DB tem string livre. Pode salvar direto OU normalizar pra sigla.
- **`meta_description`** (191/191) -> `description ou detailedDescription`
  - ABF meta_description e ~155 chars. Cabe em description (text). Decidir qual coluna alvo.
- **`gallery_urls`** (176/191) -> `galleryUrls`
  - DB armazena como TEXT (string JSON). Scraper traz list[str]. UPSERT precisa json.dumps().

### 2b. BusinessModel

- **`investment_total_min/max`** (234/191) -> `investment (NUMERIC, single)`
  - DB tem 1 valor; ABF tem range. Decidir: usar min, expandir pra _min/_max, ou string range.
- **`payback_months_min/max`** (236/191) -> `payback (INTEGER, single)`
  - Mesma decisao. ABF traz meses (e.g., 18-24); DB ja em meses (integer). Confirmar unidade.
- **`area_m2_min/max`** (192/191) -> `storeArea (INTEGER, single)`
  - DB single integer; ABF range float. Mesma decisao de range.
- **`franchise_fee_min/max`** (234/191) -> `franchiseFee (NUMERIC, single)`
  - Mesma decisao de range.
- **`working_capital_min/max`** (166/191) -> `workingCapital (NUMERIC, single)`
  - Mesma decisao de range.
- **`capital_installation_min/max`** (196/191) -> `setupCapital (NUMERIC, single)`
  - Mesma decisao de range.
- **`advertising_fee_rate`** (236/191) -> `advertisingFee (NUMERIC) + calculationBaseAdFee (string)`
  - ABF traz string ('VARIAVEL', '2%', '5,5%') que NAO bate com NUMERIC do DB. Precisa parser OU coluna text nova.
- **`advertising_fee_base`** (172/191) -> `calculationBaseAdFee`
  - Direto, mas DB e VARCHAR(191). Verificar tamanho dos valores ABF.
- **`royalties_rate`** (236/191) -> `royalties (NUMERIC) + calculationBaseRoyaltie`
  - Mesma situacao do advertising_fee_rate.
- **`royalties_base`** (204/191) -> `calculationBaseRoyaltie`
  - Direto.

---

## 3. Gaps reais (ABF tem, DB nao tem)

Cada gap propoe coluna nova OU alteracao. Migration vira da soma dessas decisoes.

| ABF field | Onde vai | Coluna proposta | Tipo proposto | Justificativa |
|---|---|---|---|---|
| `abf_updated_at` | Franchise (top-level) | `abfUpdatedAt` | `DATE` | Rastreabilidade de quando associado atualizou ficha na ABF. Diferente de lastScrapedAt (que e quando NOSSO scraper rodou). |
| `(meta) dataSource` | Franchise (novo) | `dataSource` | `VARCHAR(50)` | Diferenciar origem dos dados (manual, claimed, abf-portaldofranchising, encontresua-franquia, etc.). Permite politica de UPSERT diferenciada. |
| `business_models[].headquarter` | BusinessModel | `headquarter` | `VARCHAR(191)` | ABF traz HQ por modelo (pode diferir entre Quiosque vs Loja). DB BM nao tem. |
| `business_models[].total_units` | BusinessModel | `totalUnits` | `INTEGER` | ABF traz total por modelo (Quiosque tem 52, Loja tem 4656). DB BM nao tem. |
| `business_models[].advertising_fee_observation` | BusinessModel | `advertisingFeeObservation` | `TEXT` | Texto livre que ABF traz junto da fee. Hoje nao tem destino. |
| `business_models[].royalties_observation` | BusinessModel | `royaltiesObservation` | `TEXT` | Idem. |
| `(impl) BusinessModel.description` | BusinessModel — campo EXISTENTE | `description` | `ALTER NOT NULL -> NULL` | Hoje description e NOT NULL. Scraper nao tem description por modelo. Bloquea inserts via scraper. Decidir: alter pra nullable OU placeholder vazio. |
| `(impl) BusinessModel.photoUrl` | BusinessModel — campo EXISTENTE | `photoUrl` | `ALTER NOT NULL -> NULL` | Hoje photoUrl e NOT NULL. Scraper nao tem photoUrl por modelo. Mesmo bloqueio. Decidir igual a description. |

---

## 4. Campos DB sem correspondencia ABF

Sem acao — esses ficam como estao. ABF nao trara dados pra eles via enrichment.

### 4a. Franchise

- `abfSince` (integer)
- `averageMonthlyRevenue` (numeric)
- `averageRating` (double precision)
- `bannerUrl` (character varying)
- `brandFoundationYear` (integer)
- `businessType` (text)
- `contactId` (integer)
- `createdAt` (timestamp without time zone)
- `differentials` (jsonb)
- `facebookUrl` (character varying)
- `favoritesCount` (integer)
- `franchiseStartYear` (integer)
- `headquarterState` (character varying)
- `id` (character varying)
- `idealFranchiseeProfile` (text)
- `instagramUrl` (character varying)
- `isAbfAssociated` (boolean)
- `isActive` (boolean)
- `isReview` (boolean)
- `isSponsored` (boolean)
- `linkedinUrl` (character varying)
- `maximumReturnOnInvestment` (integer)
- `minimumReturnOnInvestment` (integer)
- `ownerId` (character varying)
- `phone` (character varying)
- `processSteps` (jsonb)
- `publicEmail` (character varying)
- `ratingSum` (integer)
- `reviewCount` (integer)
- `sku` (character varying)
- `sponsorPlacements` (jsonb)
- `status` (character varying)
- `subsegment` (character varying)
- `tagline` (character varying)
- `testimonials` (jsonb)
- `thumbnailUrl` (character varying)
- `totalUnitsInBrazil` (integer)
- `totalUnitsLastConfirmedAt` (timestamp without time zone)
- `totalUnitsUpdatedAt` (timestamp without time zone)
- `unitsEvolution` (character varying)
- `updatedAt` (timestamp without time zone)
- `videoUrl` (text)
- `whatsapp` (character varying)

### 4b. BusinessModel — todas as colunas (alem das mapeadas) ficam intactas via scraper

---

## 5. Decisoes editoriais pendentes (6 perguntas pro Breno)

**Importante:** nao abrir migration nem rodar enrichment_diff antes de receber resposta a essas.

1. **Politica de UPSERT por campo.** Pra cada campo do scraper, qual estrategia?
   - (A) Scraper e fonte de verdade (sempre sobrescreve)
   - (B) Scraper preenche so se DB esta NULL
   - (C) Scraper descartado se DB tem qualquer valor
   - (D) Caso a caso (ver exemplos)

   *Sugestao default: (B), exceto pra `abfUpdatedAt`, `lastScrapedAt`, `dataSource` que sao (A) sempre.*

2. **BusinessModel.description e photoUrl sao NOT NULL.** Como tratar?
   - (i) Migration ALTER pra nullable em ambos. Permite criar BM via scraper sem placeholder.
   - (ii) Scraper preenche `description = ''` e `photoUrl = ''` (placeholder vazio).
   - (iii) Skip BusinessModel inteiro nesta fatia — popular so Franchise. BM via scraper fica pra fatia futura.

3. **Modelagem de ranges (`_min`/`_max`).** Hoje BusinessModel tem singles (`investment`, `payback`, `franchiseFee`, etc.). ABF traz range. O que fazer?
   - (i) Usar `_min` como valor unico, descartar `_max` (perda de informacao)
   - (ii) Migration: trocar single col -> 2 cols `_min`/`_max` em todos os 6 campos afetados (mais correto, custo: migration grande)
   - (iii) Manter single + nova string `range` pra exibicao (gambiarra)

4. **Royalties/propaganda com `rate` textual ('VARIAVEL') + `observation`.** ABF traz `royalties_rate="VARIAVEL"`, `royalties_base="Compras"`, `royalties_observation=null`. DB tem `royalties NUMERIC` + `calculationBaseRoyaltie VARCHAR`. O que fazer com rate textual e observation?
   - (i) Criar colunas `royaltiesObservation TEXT` e mudar `royalties` pra texto livre
   - (ii) Manter `royalties NUMERIC` (parser tenta extrair numero, descarta se nao consegue) + nova `royaltiesObservation TEXT`
   - (iii) Concatenar tudo em `description` (gambiarra, perde tipagem)

5. **Pacote de rastreabilidade.** Adicionar 3 colunas novas em Franchise: `abfUpdatedAt DATE`, `dataSource VARCHAR(50)`, `lastScrapedAt` ja existe. OK juntar tudo numa migration?
   - (i) Sim — migration `abf_traceability` com 2 ALTER ADD COLUMN (`abfUpdatedAt`, `dataSource`)
   - (ii) So `dataSource` agora; `abfUpdatedAt` deferido pra fatia ABF mais madura

6. **Imagens — onde sincar e como nomear no DB?**
   - Path EC2 proposto: `/home/ubuntu/mercadofranquia-uploads/abf/{slug}/`
   - URL publica: `https://mercadofranquia.com.br/uploads/abf/{slug}/...`
   - DB salva URL absoluta OU path relativo `/uploads/abf/{slug}/logo.jpg`?
   *Sugerido: path relativo (segue padrao de `logoUrl` atual em `/uploads/...`).*

---

## Estatisticas dos 191 JSONs

Top 25 campos por presenca (descartando null/empty):

| Campo | Presenca |
|---|---|
| `business_models[].name` | 236/191 (123%) |
| `business_models[].headquarter` | 236/191 (123%) |
| `business_models[].payback_months_min` | 236/191 (123%) |
| `business_models[].payback_months_max` | 236/191 (123%) |
| `business_models[].advertising_fee_rate` | 236/191 (123%) |
| `business_models[].royalties_rate` | 236/191 (123%) |
| `business_models[].franchise_fee_min` | 234/191 (122%) |
| `business_models[].franchise_fee_max` | 234/191 (122%) |
| `business_models[].investment_total_min` | 234/191 (122%) |
| `business_models[].investment_total_max` | 234/191 (122%) |
| `business_models[].total_units` | 230/191 (120%) |
| `business_models[].royalties_base` | 204/191 (106%) |
| `business_models[].capital_installation_min` | 196/191 (102%) |
| `business_models[].capital_installation_max` | 196/191 (102%) |
| `business_models[].area_m2_min` | 192/191 (100%) |
| `business_models[].area_m2_max` | 192/191 (100%) |
| `slug` | 191/191 (100%) |
| `scraped_at` | 191/191 (100%) |
| `source_url` | 191/191 (100%) |
| `segment_abf_id` | 191/191 (100%) |
| `segment_abf_name` | 191/191 (100%) |
| `name` | 191/191 (100%) |
| `meta_description` | 191/191 (100%) |
| `abf_updated_at` | 185/191 (96%) |
| `scraped_website` | 185/191 (96%) |
