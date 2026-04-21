# Sprint 2 Frontend — Cadastro unificado de franquia

**Data:** 2026-04-21  
**Status:** ✅ Completa (build passa, 0 erros TS/lint)  
**Deploy:** Pendente (aguarda deploy Sprint 1 — segunda 23/04)

---

## Objetivo

Permitir que qualquer user logado (MEMBER ou FRANCHISOR) cadastre franquias pelo painel `/franqueador/minhas-franquias`, unificando os fluxos de:

- **Primeira marca** (user MEMBER) → cria FranchisorRequest + Franchise; admin aprova → user vira FRANCHISOR
- **Marca adicional** (user FRANCHISOR) → cria só Franchise
- **Reivindicação de marca existente** (qualquer role) → cria FranchisorRequest com mode=EXISTING

Frontend decide qual endpoint chamar baseado em role + mode; user vê uma única ação ("Cadastrar franquia").

---

## Decisões arquiteturais principais

### 1. Não há rota `/franqueador/solicitar`
Descartada após múltiplas iterações. O mental model correto é: user quer **cadastrar marca**, não "virar franqueador". Role FRANCHISOR é detalhe de implementação backend.

### 2. Endpoint unificado é frontend-only
Backend mantém 2 endpoints separados:
- `POST /users/franchisor-request` — primeira marca ou reivindicação
- `POST /franchisor/franchises` — marca adicional (exige role FRANCHISOR)

Hook `useSubmitFranchiseRequest` faz o roteamento:
- Mode EXISTING → sempre `franchisor-request` (qualquer role)
- Mode NEW + FRANCHISOR → `franchisor/franchises`
- Mode NEW + não-FRANCHISOR → `franchisor-request`

### 3. MVP enxuto — sem campos opcionais de marca
Form pede apenas:
- NEW: streamName (nome da marca)
- EXISTING: franchiseId + claimReason

Campos de enriquecimento (description, segment, logoUrl, headquarter, etc.) são preenchidos depois no painel, após aprovação.

### 4. Bloqueio estrito por role no middleware
Regras em `middleware.ts` (ordem importa):
```
/franqueador          → qualquer logado (page redireciona pra /minhas-franquias)
/franqueador/minhas-franquias → qualquer logado (componente decide UI por role)
/franqueador/*        → apenas FRANCHISOR
```

---

## Arquivos criados (2)

- `web/src/components/ui/ModeSelectorCard.tsx` (115 linhas) — Cards clicáveis com 2-4 opções, usa `role="radiogroup"` + `aria-checked`, brand color `#E25E3E`, responsivo
- `web/src/hooks/franchises/useSubmitFranchiseRequest.ts` (98 linhas) — Mutation que decide endpoint por role + mode, invalida caches `myFranchises` e `franchisor-request/my-request`

## Arquivos modificados (5)

- `web/src/middleware.ts` — 3 regras pra `/franqueador/*` (root + minhas-franquias + genérica)
- `web/src/components/franchisors/panels/franchises/CreateAdditionalFranchiseForm.tsx` — reescrito (255→185 linhas), agora suporta NEW + EXISTING via ModeSelectorCard, usa hook unificado + schema FranchisorRequestFormSchema
- `web/src/components/franchisors/panels/franchises/MyFranchisesList.tsx` — adiciona estado "primeiro acesso" pra user não-FRANCHISOR (card "Cadastre sua franquia" com CTA)
- `web/src/components/header/HeaderRightActions.tsx` — CTA "Cadastrar franquia" (desktop) pra MEMBER e roles legados não-FRANCHISOR/ADMIN
- `web/src/components/header/shared/RenderMobileLayout.tsx` — CTA "Cadastrar franquia" no menu mobile expandido pros mesmos roles
- `web/src/app/(franchisor)/franqueador/minhas-franquias/page.tsx` — prop `isOpen` → `open` (alinhar com novo form)

---

## Dead code identificado (cleanup futuro)

- `web/src/hooks/franchises/useCreateAdditionalFranchise.ts` — sem consumers (substituído por `useSubmitFranchiseRequest`)
- `web/src/schemas/franchises/CreateAdditionalFranchise.ts` → o **schema Zod** virou órfão, mas a **interface `CreateAdditionalFranchiseDto`** continua em uso (services/franchises.ts + useSubmitFranchiseRequest.ts). Cleanup deve separar interface do schema ou deletar só o schema.

---

## Bugs pré-existentes sinalizados (não-bloqueadores)

- `GET /users/franchisor-request/my-request` (backend) — usa `.scalar()` sem `order_by` + `limit(1)`. Quando user tem múltiplas requests retorna uma indefinida. Fix trivial. Fora do escopo desta sprint porque o frontend atual não depende do comportamento correto.
- Model SQLAlchemy `FranchisorRequest.userId` ainda tem `unique=True`, divergente do schema em prod (dropado pela migration). Não quebra nada em runtime, mas cria divergência silenciosa.
- 9 warnings de lint pré-existentes em arquivos não-tocados.

---

## Próximos passos

### Imediato (segunda 23/04)
1. **Deploy Sprint 1 primeiro** (já tem procedimento documentado em `2026-04-20-frontend-sprint1.md`)
2. Smoke test em produção
3. Deploy Sprint 2 (rsync + build + restart mf-web)
4. Smoke test do fluxo novo:
   - Login como user novo → clica "Cadastrar franquia" no header → abre `/minhas-franquias` → vê card "primeiro acesso" → clica CTA → modal abre com ModeSelectorCard → submete NEW → vê toast sucesso → admin aprova → user vira FRANCHISOR
   - Login como FRANCHISOR → clica "Nova marca" → modal abre → seleciona NEW → submete → vê como marca adicional PENDING
   - Login como FRANCHISOR → clica "Nova marca" → seleciona EXISTING → submete reivindicação

### Cleanup futuro (baixa prioridade)
- Deletar `useCreateAdditionalFranchise` e separar DTO do schema Zod
- Fix do bug `GET /my-request` com order_by + limit
- Remover `unique=True` do model `FranchisorRequest.userId`

### Backlog Sprint 3 candidatos
- Campos opcionais no form (description, logoUrl, segment, etc.) via "Completar depois" na página da marca
- Autocomplete pro Select de reivindicação (hoje carrega ~1400 opções)
- Painel admin pra marcas adicionais PENDING (hoje só aprova via API direta)

---

## Resumo de decisões difíceis tomadas (audit trail)

Durante a sessão, o plano mudou 6+ vezes antes de convergir. Evolução:

1. Inicialmente proposto: página `/franqueador/solicitar` separada
2. Depois: unificar em `/franqueador`
3. Depois: bloqueio estrito de FRANCHISOR
4. Reviravolta final: eliminar /solicitar, tudo em `/minhas-franquias`

Gatilho da reviravolta: insight de que "user não quer virar franqueador, quer cadastrar marca — resto é detalhe interno". Essa visão centrada no user invalidou a distinção artificial entre "solicitar acesso" e "cadastrar marca adicional".

---

## Postmortem — bug pós-deploy (.env.local na EC2)

**Sintoma:** Após deploy, `/ranking` e páginas que consomem API mostravam "Nenhuma franquia encontrada". Curl direto na API funcionava, mas o frontend não conseguia fazer fetch.

**Causa raiz:** O arquivo `.env.local` na EC2 (resíduo de deploy antigo antes de termos `--exclude .env.*` no rsync) continha `NEXT_PUBLIC_API_URL=http://18.230.68.207`. Next.js prioriza `.env.local` sobre `.env.production`, então o build congelou URL HTTP no bundle. Browser em HTTPS bloqueou as chamadas por mixed content.

**Fix:** Rename `.env.local` → `.env.local.off` + rebuild + restart mf-web. Com `.env.local` removido, `.env.production` (com URL HTTPS correta) venceu a precedência.

**Tempo de detecção/fix:** ~15-20min após deploy.

**Prevenção:**
1. **Já aplicado:** `--exclude '.env.*'` no rsync (deploy de hoje preservou o arquivo, não criou novo, mas também não sobrescreveu o que já estava lá)
2. **A fazer:** Remover `.env.local` definitivamente da EC2 após confirmar estabilidade por 24-48h
3. **A fazer:** Adicionar check no journal de próximos deploys: verificar `cat .env.local` antes de `npm run build` e falhar se o arquivo existir

**Lição:** Variáveis `NEXT_PUBLIC_*` no Next.js são congeladas no bundle em build-time. Mudança requer rebuild + restart, não apenas restart. Ordem de precedência dos .env é crítica e documentada em https://nextjs.org/docs/basic-features/environment-variables
