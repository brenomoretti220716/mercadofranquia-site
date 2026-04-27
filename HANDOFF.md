# Handoff — Mercadofranquia

## Estado atual (27/04/2026)

Branch ativa: `feat/fatia-1-8-handoff-editorial`

### Em desenvolvimento

- **Fatia 1.8 — Página pública editorial v10**
  - Bloco A (Banner + Hero + Modelos): completo
  - Bloco B (Sobre + Vídeo + Stepper): pendente
  - Bloco C (Diferenciais + Perfil + Galeria): pendente
  - Bloco D (Reputação): pendente
  - Bloco E (Lead form): pendente

### Backlog

#### Fatia 1.9 — Sistema de ranges agregados (PRIORIDADE)

Os 5 campos secundários do `BusinessModel` adicionados na Fatia 1.8.1
(`franchiseFee`, `royalties`, `advertisingFee`, `workingCapital`,
`setupCapital`) estão **ocultos da página pública** por enquanto. São
coletados no editor pra alimentar futuro sistema de ranges.

Quando virar prioridade:
- Calcular min/max desses campos a partir dos modelos cadastrados
- Criar bloco "Indicadores gerais da rede" na página pública
- Mostrar ranges como "Royalties: 4,5%–6%", "Capital de giro: R$ 25k–R$ 50k"
- Lógica adaptativa: se franquia tem só 1 modelo, mostra valor único; 2+ modelos, mostra range

#### Fatia 1.8.2 — Editor de franquia (campos novos)

Atualizar o editor pra coletar os novos campos do `BusinessModel`:
- `investment`, `payback`, `profitability` (5 métricas-chave da página pública)
- + os 9 campos secundários da Fatia 1.8.1 (`franchiseFee`, `royalties`,
  `advertisingFee`, `workingCapital`, `setupCapital`, `averageMonthlyRevenue`,
  `storeArea`, `calculationBaseRoyaltie`, `calculationBaseAdFee`)

Também atualizar `routers/business_models.py:_serialize` (endpoint legacy
`/api/business-models/franchise/{slug}`) pra retornar todos esses campos —
hoje só `serialize_business_model` em `serializers.py` (consumido por
`/api/franchises/{slug}` e `/ranking`) está atualizado.

#### Outros backlogs

- Bug `FranchisorEditing.tsx` (cnpj/phone null check)
- Refactor enum `FranchisorRequestStatus` duplicado
- Rotação de credenciais expostas (Postgres `mf_user`, AWS keys, `JWT_SECRET`)
