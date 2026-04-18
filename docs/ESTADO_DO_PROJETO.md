# Estado do Projeto — Mercado Franquia

Documento-espelho do estado real do projeto em 18 de abril de 2026.
Substitui o contexto "de cabeça" — próxima sessão começa daqui.

---

## 1. Arquitetura atual

### Stack em produção

| Camada       | Tecnologia                            | Rodando em                               |
| ------------ | ------------------------------------- | ---------------------------------------- |
| Frontend     | Next.js 15.5 standalone + React 19    | systemd `mf-web` (porta 3000)            |
| Backend      | FastAPI + SQLAlchemy + Uvicorn        | systemd `mf-api` (porta 4000, 2 workers) |
| Banco        | PostgreSQL 16 nativo (sem Docker)     | localhost:5432                            |
| Proxy/TLS    | Nginx + Certbot (auto-renewal)        | portas 80/443                             |
| Scraping     | systemd timer `mf-macro-sync.timer`   | diário 03:00 BRT                          |
| Uploads      | Disco local (`/home/ubuntu/.../uploads`) | servido via Nginx `/uploads/`             |

### Stack de dev

- **Editor:** Mac local, projeto em `~/Developer/mercadofranquia/`
- **Repo GitHub:** `brenomoretti220716/mercadofranquia-site`
- **Deploy:** `rsync` do Mac → EC2 (build do Next no EC2; restart systemd)

---

## 2. Estado do banco

Tabelas com dados vivos:

| Tabela            | Linhas | Origem                                   |
| ----------------- | -----: | ---------------------------------------- |
| `Franchise`       |  1 404 | import histórico + scraping legado       |
| `CagedBcb`        |    876 | sync diário via `mf-macro-sync`          |
| `MacroIbge`       |    416 | sync diário via `mf-macro-sync`          |
| `AbfRevenue`      |    133 | extração de relatórios ABF               |
| `AbfSegmentEntry` |     49 | importação manual de PDFs ABF            |
| `AbfUnitsRanking` |     40 | extração de relatórios ABF               |
| `AbfReport`       |     28 | upload de relatórios ABF                 |
| `AbfIndicator`    |     14 |                                           |
| `User`            |      5 | só admins                                 |

Tabelas criadas mas **sem dados** (features codadas, nunca populadas):

- `News`, `NewsComment`, `Review`, `ReviewResponse`, `Favorite`,
  `BusinessModel`, `FranchisorRequest`, `QuizSubmission`,
  `FranchiseMonthlyUnits`, `_FranchiseFranchisees`.

Uploads em disco:

- **11 493 logos** de franquias em `uploads/franchises/`.

---

## 3. Camada de ingestão (scraping)

### O que roda hoje

`deploy/ec2/app/services/macro_sync.py` — 514 linhas, versionado.

Alimenta diariamente às 03:00 BRT:

- **9 séries BCB** (SGS API): Selic, IPCA, câmbio etc.
- **2 agregados IBGE** + **1 PMC** (SIDRA API).
- **6 séries CAGED** (via BCB/SGS).
- Popula: `CagedBcb`, `MacroIbge`, `MacroBcb`.

Ativado por `systemctl enable --now mf-macro-sync.timer`.

### O que **não** é automatizado

- **Relatórios ABF** — upload manual em `/admin/upload` alimenta
  `AbfReport`, `AbfRevenue`, `AbfUnitsRanking`, `AbfIndicator`,
  `AbfProjection`, `AbfSegmentEntry`.
- **Franquias** — base atual veio de carga histórica; sem refresh automático.
- **Logos** — coletados uma vez por scrapers JS hoje arquivados (MySQL legado).
- **Notícias** — **não há pipeline** (`News` está zerada).
- **Reviews / Favorites / BusinessModels** — sem ingestão.

---

## 4. Camada de exposição (API)

### Routers FastAPI ativos

```
abf_segments    franchises           quiz
auth            franchisor_requests  ranking
big_numbers     news                 register
business_models notifications        reviews
favorites       fontes               scraping
                                     statistics
                                     users
```

Novos nesta sessão:

- **`GET /fontes/admin/status`** — agrega estado das tabelas macro.
  Protegido por `require_role("ADMIN")`. Read-only.

### Endpoints ainda **não expostos** (apesar das tabelas terem dados)

- `AbfRevenue`, `AbfProjection`, `AbfIndicator`, `AbfUnitsRanking`,
  `CagedBcb`, `MacroIbge`, `MacroBcb` → nenhum endpoint público.
  Consequência: `TickerBar` e `MacroIndicators` na home renderizam **mock**.

---

## 5. Camada de apresentação (frontend)

### Rotas admin hoje

- `/admin` — dashboard
- `/admin/franquias`, `/admin/franqueados`, `/admin/franqueadores`,
  `/admin/administradores`
- `/admin/noticias`
- `/admin/segmentos-abf`, `/admin/big-numbers`, `/admin/patrocinados`
- **`/admin/fontes`** — novo nesta sessão (monitoramento do macro-sync)

### Rotas públicas

- `/` (home com hero + segmentos + reviews mock)
- `/login`, `/quiz`, ... (estrutura existe, conteúdo mínimo)

### Pontos com mock/placeholder hoje

- `TickerBar` na home — valores hardcoded
- `MacroIndicators` na home — valores hardcoded
- `ReviewsSection` — tabela `Review` vazia
- `NewsSection` — tabela `News` vazia

---

## 6. Fluxo de deploy

### Frontend

```bash
# No Mac
rsync -avz --exclude='node_modules/' --exclude='.next/' --exclude='.git/' \
  ~/Developer/mercadofranquia/web/ \
  ubuntu@<EC2>:~/mercadofranquia-web/

# No EC2
cd ~/mercadofranquia-web
NODE_OPTIONS='--max-old-space-size=2048' npm run build
cp -r .next/static .next/standalone/.next/static
cp -r public .next/standalone/public
sudo systemctl restart mf-web
```

**Build consome ~900 MB de RAM; a t2.medium tem 4 GB e já roda FastAPI +
Postgres.** É apertado. Eventualmente o build deve sair para CI.

### Backend

```bash
# No Mac
rsync -avz ~/Developer/mercadofranquia/deploy/ec2/app/ \
  ubuntu@<EC2>:~/mercadofranquia-api/app/

# No EC2
sudo systemctl restart mf-api
```

### Systemd units (fonte-de-verdade versionada)

- `deploy/ec2/systemd/mf-api.service.template` — placeholders para secrets
- `deploy/ec2/systemd/mf-web.service`
- `deploy/ec2/systemd/mf-macro-sync.service`
- `deploy/ec2/systemd/mf-macro-sync.timer`
- `deploy/ec2/systemd/README.md` — instruções de install e troubleshooting
- `deploy/ec2/systemd/mf-api.service` (arquivo real com secrets — **no .gitignore**)

> **Atenção:** `deploy/ec2/app/db.py` **exige** `DATABASE_URL` no env
> (desde 18/abr). Sem essa variável setada, o app não sobe (levanta
> `RuntimeError` explícito). Em produção o systemd `mf-api.service`
> seta a var, então deploy normal funciona. Para rodar localmente,
> `export DATABASE_URL=postgresql+psycopg://...` antes.

---

## 7. O que foi decidido (e o que foi descartado)

### Decisões tomadas nesta sessão

1. **Foco exclusivo em `mercadofranquia-site`.** O plano de "fusão
   Intelligence → Site" foi cancelado.
2. **Projetos legados arquivados fora do dev env:** o antigo NestJS+MySQL,
   o frontend Next 16 paralelo ("inteligencia"), scrapers JS, dumps SQL.
3. **Backup zip de referência** criado em `~/BackupsMercadoFranquia/`
   (775 MB, inclui git history das pastas legadas).
4. **`fontes/` commitado** — faz sentido agora que o scraping que ele
   expõe está versionado e ativo.

### Decisões pendentes

- **Pipeline de notícias**: não há — `News` está zerada. Próximo candidato
  a feature real.
- **Expor dados macro no frontend público**: remover mocks do `TickerBar`
  e `MacroIndicators` exige endpoint novo (`/api/market-indicators` ou
  similar).
- **Split do `models.py`**: 44 KB num arquivo só — candidato a refactor
  quando for mexer pesado em schema.
- **Build do Next em CI**: mitiga risco de OOM na t2.medium em produção.

---

## 8. Infra — pontos de atenção

- ~~Secrets atuais em produção (Postgres e JWT) foram rotacionados
  nesta sessão, mas os valores saíram no chat~~ **✅ Rotacionado em
  momento privado em 18/abr/2026 (segunda rotação). Novos secrets
  salvos em `~/.mf-secrets` no EC2 (chmod 600) — guardar em gerenciador
  de senhas e esquecer o arquivo.**
- **CORS** do FastAPI está em `*` no systemd — ok para o momento, mas
  apertar para a lista de origens reais antes de ter tráfego real.
- **Backup automatizado do Postgres** — não existe. Os scripts antigos
  (`mf-backup/`) eram para MySQL+Docker e foram removidos. Precisa ser
  reescrito para PG+systemd.
- **Apenas 1 instância EC2, sem Elastic IP** — se a instância reiniciar,
  IP muda e DNS quebra.

---

## 9. O que não está no código

Conhecimento tácito que precisa ser lembrado:

- **Schema usa PascalCase** (`"User"`, `"Franchise"`, etc.) por herança
  do Prisma — SQL manual exige aspas duplas, SQLAlchemy abstrai.
- **`NEXT_PUBLIC_*` vars bake em build-time**. Mudar essas variáveis
  exige rebuild completo do frontend, não apenas restart do systemd.
- **Logo rendering:** usar
  `src={\`${process.env.NEXT_PUBLIC_API_URL ?? ''}${franchise.logoUrl}\`}`
  com `unoptimized` no `next/image`.
- **CNAE 7740-3/00** (holding de franquias) tem alta subnotificação na
  Receita Federal — útil para **enriquecimento**, não para discovery.
- **Padrão editorial** (quando houver conteúdo): Bloomberg / Economist /
  Endeavor Brasil. Títulos-tese, dados na primeira frase, citação
  explícita de fonte (ex: "ABF, 2025"), 600–800 palavras densas.

---

## 10. Status sanitário — 18/abr/2026

- ✅ Repo limpo, working tree clean
- ✅ Nenhum dump SQL ou senha hardcoded no repo atual
- ✅ `.gitignore` cobrindo `__pycache__`, `.pyc`, `mf-api.service`
- ✅ Scraping macro versionado + rodando
- ✅ Systemd units versionados (com template sanitizado)
- ✅ Backup local validado
- ✅ Secrets rotacionados em momento privado — chat nunca viu os valores novos
- ✅ Zero senhas hardcoded em arquivos ativos do repo (scripts históricos arquivados)
- 🟡 Tabelas de conteúdo (News, Review etc.) esperando pipeline
- 🟡 Painel `/admin/fontes` commitado mas ainda não deployed no EC2

---

*Documento gerado em 18/abr/2026, atualizado no mesmo dia após segunda
rotação de secrets e sanitização de senhas hardcoded residuais. Atualizar quando houver mudança estrutural (nova feature
grande, mudança de stack, migração).*
