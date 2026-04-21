# Sprint 1 Frontend — Mercado Franquia

**Data:** 2026-04-20 (sexta)
**Status:** Desenvolvimento concluído, deploy agendado pra segunda (2026-04-23)

---

## ✅ Entregue na sessão

| Métrica | Valor |
|---|---|
| Etapas concluídas | 6 (schemas, services, queries, rota, componentes novos, cleanup legados) |
| Arquivos criados | 5 |
| Arquivos reescritos | 6 |
| Arquivos deletados | 3 |
| TS errors | 82 → 0 |
| Build Next.js | ✓ Passa (8.7s, 26 páginas geradas) |
| Standalone output | ✓ Gerado em `.next/standalone/` |

### Arquivos criados
- `web/src/components/franchisors/panels/franchises/FranchiseStatusBanner.tsx`
- `web/src/components/franchisors/panels/franchises/MyFranchisesList.tsx`
- `web/src/components/franchisors/panels/franchises/CreateAdditionalFranchiseForm.tsx`
- `web/src/hooks/franchises/useCreateAdditionalFranchise.ts`
- `web/src/schemas/franchises/CreateAdditionalFranchise.ts`

### Arquivos reescritos
- `web/src/app/(franchisor)/franqueador/page.tsx` — agora server redirect
- `web/src/app/(franchisor)/franqueador/minhas-franquias/page.tsx`
- `web/src/schemas/users/FranchisorRequest.ts` — schema novo com mode NEW/EXISTING
- `web/src/services/users.ts` — 7 funções franchisor-request atualizadas
- `web/src/hooks/users/useFranchisorRequest.ts`
- `web/src/components/admin/panels/users/franchisors-controll/FranchisorRequestModal.tsx`
- `web/src/components/admin/panels/users/franchisors-controll/franchisorRequestsTable/FranchisorRequestsTableRow.tsx`
- `web/src/components/admin/panels/users/franchisors-controll/franchisorRequestsTable/FranchisorRequestsTableHeader.tsx`
- `web/src/components/admin/panels/users/franchisors-controll/FranchisorsPanel.tsx`
- `web/src/components/pages/perfil/PerfilPageClient.tsx` — removido Accordion

### Arquivos deletados
- `web/src/components/login/FranchisorRequestAccordion.tsx`
- `web/src/components/franchisors/panels/franchises/FranchisorSelectedFranchise.tsx`
- `web/src/components/ui/skeletons/FranchisorSelectedFranchiseSkeleton.tsx`

### Fluxo funcional novo
1. Franqueador loga → redirect → `/franqueador/minhas-franquias`
2. Vê lista de suas franquias com banner de status (APPROVED verde / PENDING amarelo / REJECTED vermelho)
3. Clica "Nova marca" → modal RHF+Zod
4. Submete → `POST /franchisor/franchises` → toast + lista atualizada com PENDING
5. Admin aprova via painel → user recebe email + status vira APPROVED

---

## 🔐 Snapshot pré-deploy (rollback point)

Criado **antes** do deploy pra garantir rollback rápido se algo quebrar.

| Item | Valor |
|---|---|
| **Snapshot ID** | `snap-00eab532833796a95` |
| **Name tag** | `pre-sprint1-frontend-deploy` |
| **Source volume** | `vol-000a86f3e70f95235` (80 GiB, gp3) |
| **Instance source** | `i-0ba72b025e039aaf0` (site-mercado-franquia) |
| **Região** | `sa-east-1` |
| **Criado em** | 2026-04-20 ~20:10 BRT |

### Rollback procedure (se der problema pós-deploy)

1. Stop instance `site-mercado-franquia` (i-0ba72b025e039aaf0)
2. Detach `vol-000a86f3e70f95235`
3. Create volume from `snap-00eab532833796a95` (80 GiB, gp3, AZ `sa-east-1a`)
4. Attach novo volume à instance em `/dev/sda1` (root)
5. Start instance
6. Verifica no browser que site funciona (`https://mercadofranquia.com.br`)

**Rollback estimado:** ~10-15 minutos.

---

## 🚀 Plano de deploy (segunda 2026-04-23)

### Pré-deploy
```bash
# 1. Conferir que código local tá igual ao do sexta
cd ~/Developer/mercadofranquia && git status

# 2. Rodar build local de novo pra confirmar que ainda passa
cd ~/Developer/mercadofranquia/web && NODE_OPTIONS='--max-old-space-size=2048' npm run build
```

### Deploy
```bash
# 1. rsync pra EC2
cd ~/Developer/mercadofranquia && rsync -avz \
  --exclude 'node_modules/' \
  --exclude '.next/' \
  --exclude '.git/' \
  --exclude '.env.local' \
  web/ ubuntu@18.230.68.207:~/mercadofranquia-web/

# 2. Build remoto + copia static + copia public
ssh ubuntu@18.230.68.207 "cd ~/mercadofranquia-web && \
  NODE_OPTIONS='--max-old-space-size=2048' npm run build && \
  cp -r .next/static .next/standalone/.next/static && \
  cp -r public .next/standalone/public"

# 3. Restart service
ssh ubuntu@18.230.68.207 "sudo systemctl restart mf-web && \
  sleep 2 && sudo systemctl status mf-web --no-pager | head -15"

# 4. Smoke test HTTP
curl -sI https://mercadofranquia.com.br/franqueador/minhas-franquias | head -5
curl -sI https://mercadofranquia.com.br/ | head -5

# 5. Logs em tempo real
ssh ubuntu@18.230.68.207 "sudo journalctl -u mf-web -n 30 --no-pager"
```

### Smoke test manual (browser)

- [ ] `/` (homepage) carrega
- [ ] `/franqueador` redireciona pra `/franqueador/minhas-franquias`
- [ ] Login como franqueador (ex: `breno.moretti@mercadofranquia.com.br`)
- [ ] Ver lista de marcas com banner de status correto
- [ ] Clicar "Nova marca" → modal abre
- [ ] Preencher apenas streamName → submit → toast sucesso + PENDING aparece na lista
- [ ] Logout + login como admin (`admin@franchise.com`)
- [ ] `/admin/franqueadores` lista requests no formato novo (colunas: Marca/Tipo/Franquia vinculada/Usuário/Status/Data/Ações)
- [ ] Abrir modal admin de uma request PENDING
- [ ] Aprovar → ver email chegar
- [ ] Logar como o user dono → marca vira APPROVED no painel

---

## 📝 Gap conhecido — Sprint 2

### Form público de solicitar virar franqueador

O `FranchisorRequestAccordion` foi deprecado. Agora **não existe UI** pra alguém não-franqueador solicitar virar franqueador (fluxo NEW ou EXISTING).

Backend pronto (POST `/users/franchisor-request` com `mode: NEW | EXISTING`), schemas prontos (`FranchisorRequestFormSchema` com superRefine), só falta criar a página/componente.

**Rota sugerida:** `/cadastro/franqueador` ou `/franqueador/solicitar`
**Entrada sugerida:** CTA no header (quando user não-franqueador logado) ou landing dedicada.

---

## 🧹 Pendências acumuladas

### Segurança — rotação de credenciais expostas
- [ ] Senha Postgres `mf_user`
- [ ] AWS Access/Secret Keys (IAM user `mercadofranquia-api-ses`)
- [ ] `JWT_SECRET`

### Git — commits untracked
- [ ] Backend Sprint 1: `deploy/ec2/app/services/hubspot_client.py`, `ses_mailer.py`, `constantes.py`, `models.py` edits, routers novos, `user_serializers.py`, `utils/slug.py`
- [ ] Frontend Sprint 1: tudo descrito na seção "Arquivos criados/reescritos/deletados" acima

### HubSpot — cleanup de test data
- [ ] Deletar contacts/companies de teste: Teste E2E, Teste Claim, Pizza Express, Marca Pra Rejeitar, Teste Email Fix

### AWS — snapshot lifecycle
- [ ] Confirmar que snapshot `snap-00eab532833796a95` ficou `Completed` (não `Pending`)
- [ ] Depois do deploy bem-sucedido em ~1 semana, pode deletar esse snapshot (política automática já faz backup diário)

---

## 📌 Contexto técnico (referência)

### Infraestrutura
- **Instância EC2:** `i-0ba72b025e039aaf0` (site-mercado-franquia)
- **IP público:** `18.230.68.207`
- **SSH:** `ubuntu@18.230.68.207`
- **Região:** `sa-east-1`
- **Tipo:** t2.medium
- **Disk:** 80 GiB gp3

### Stack
- **Frontend:** Next.js 15.5.9 App Router standalone (port 3000, service `mf-web`)
- **Backend:** FastAPI + uvicorn (port 4000, service `mf-api`)
- **DB:** PostgreSQL (port 5432, user `mf_user`, db `mercadofranquia`)
- **Nginx:** reverse proxy (`/` → Next, `/api/` → FastAPI, `/uploads/` → static)
- **TLS:** Certbot (auto-renewal via systemd timer)

### Endpoints novos da Sprint 1 (backend + frontend integrados)
- `GET /franchisor/franchises/me` — lista Franchises do user autenticado
- `POST /franchisor/franchises` — cria franquia adicional (franqueador aprovado)
- `POST /franchises/admin/{id}/approve` — admin aprova Franchise
- `POST /franchises/admin/{id}/reject` — admin rejeita Franchise
- `POST /admin/franchisor-requests/{id}/reopen` — admin reabre request rejeitada
- `POST /users/franchisor-request` — agora aceita JSON com `mode: NEW | EXISTING`

---

**Bom descanso. 👋**
