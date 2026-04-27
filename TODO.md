# TODO — Pendências priorizadas

## Pendente — próxima sessão

### Deploy Fatia 1.8 em produção EC2

Branch `main` já tem o código mergeado (commit `24acbad`), mas deploy ainda não foi feito.

**Ordem correta** (backend antes do frontend):

#### 1. Aplicar migrations Alembic no EC2

```bash
ssh ubuntu@18.230.68.207
cd ~/mf-api
source venv/bin/activate
alembic upgrade head
sudo systemctl restart mf-api
```

Migrations a aplicar (encadeadas, todas idempotentes via `alembic_version`):

- `c4d8e9a1b3f2` — `BusinessModel`: 9 campos financeiros (`franchiseFee`, `royalties`, `advertisingFee`, `workingCapital`, `setupCapital`, `averageMonthlyRevenue`, `storeArea`, `calculationBaseRoyaltie`, `calculationBaseAdFee`)
- `e7a3f1d8b9c2` — `BusinessModel`: `investment` + `payback`
- `b5a2c91e7f4d` — `BusinessModel`: `profitability`

Todas adicionam colunas NULLABLE sem DEFAULT — risco zero pras franquias já cadastradas.

#### 2. Build + deploy do frontend

```bash
cd web && npm run build:deploy
rsync -avz --delete .next/standalone/ ubuntu@18.230.68.207:/home/ubuntu/mercadofranquia-web/.next/standalone/
ssh ubuntu@18.230.68.207 "sudo systemctl restart mf-web"
```

#### 3. Validação pós-deploy

```bash
# Endpoint público responde 200 com novos campos
curl https://mercadofranquia.com.br/api/franchises/qualquer-slug/ranking | jq '.data.franchiseWithRanking | { businessModelsCount: (.businessModels | length), reviewsCount: (.reviews | length) }'
```

**Atenção:** após o deploy, validar que franquias EXISTENTES em prod (sem os campos novos preenchidos) continuam renderizando. O componente faz skip-if-null mas testar com franquia real pra confirmar:

- Franquia sem `businessModels` → bloco Modelos cai no Cenário A (ficha técnica enxuta)
- Franquia sem dados financeiros → bloco Modelos some inteiro
- Franquia sem reviews → bloco Reputação some inteiro
- Franquia sem `description` → bloco Sobre some inteiro
- Franquia sem `videoUrl` → bloco Vídeo some inteiro
- Franquia sem `processSteps` → bloco Como funciona some inteiro
- Franquia sem `differentials` → bloco Diferenciais some inteiro
- Franquia sem `idealFranchiseeProfile` → bloco Perfil ideal some inteiro
- Franquia sem `galleryUrls` → bloco Galeria some inteiro

#### 4. Cleanup pós-deploy bem-sucedido

- Deletar branches locais órfãs:
  ```bash
  git branch -D feat/fatia-1-6-fullwidth-and-reviews-redesign
  git branch -D feat/fatia-1-7-sidebar-sticky-and-review-tweaks
  ```
- Mover este TODO de "Pendente" pra "Concluído" no histórico ou apagar a entrada
