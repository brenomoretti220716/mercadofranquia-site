# Deploy EC2 — Mercado Franquia API

Artefactos prontos e **testados localmente contra Postgres real**.

## Conteúdo do diretório

```
deploy/ec2/
├── app/
│   ├── __init__.py
│   ├── main.py               FastAPI app — wire dos routers + CORS + /health
│   ├── db.py                 engine SQLAlchemy + session factory
│   ├── models.py             20 modelos SQLAlchemy 2.0 (Franchise, User, ...)
│   ├── serializers.py        ORM → dict no formato que o Next.js consome
│   ├── security.py           JWT (HS256) + bcrypt + get_current_user() dep
│   ├── validators.py         CPF / CNPJ / telefone BR (portados do NestJS)
│   ├── user_serializers.py   User / UserProfile / FranchisorRequest → dict
│   ├── profile_completion.py calculador de completude (9 campos, %)
│   └── routers/
│       ├── __init__.py
│       ├── auth.py               POST /auth/{login,validate,forgot/verify/reset/resend-*}
│       ├── register.py           POST /users/register/{step-one,step-two}
│       ├── users.py              GET|PUT /users/me, PUT /users/me/password,
│       │                         GET /users/me/profile-completion,
│       │                         POST /users/me/{request,verify}-email-change,
│       │                         PUT /users/profile
│       ├── franchisor_requests.py POST /users/franchisor-request (multipart),
│       │                         GET /users/franchisor-request/my-request
│       ├── franchises.py         GET /franchises, /franchises/count, /franchises/{slug}
│       ├── ranking.py            GET /ranking
│       ├── news.py               GET /news (+search/category), /news/{id},
│       │                         GET|POST /news/{id}/comments
│       ├── favorites.py          GET /favorites, /favorites/ids, /favorites/check/{slug},
│       │                         POST /favorites/{slug}, /favorites/{slug}/toggle,
│       │                         DELETE /favorites/{slug}
│       ├── reviews.py            GET /reviews/franchise/{slug}, franchisee check,
│       │                         POST /reviews/{slug}
│       ├── quiz.py               GET|POST /quiz, /quiz/profile, /quiz/results
│       │                         (scoring simplificado — ver "Quiz scoring caveat")
│       └── notifications.py     GET /notifications, /notifications/stats,
│                                 PATCH /notifications/mark-read, POST /mark-all-read,
│                                 PUT /notifications/{id}/read, DELETE /notifications/{id}
├── migrate.py                MySQL → Postgres migração (conversão de tipos + load)
├── mf-api.service            systemd unit
├── mercadofranquia.nginx     site Nginx (/api/ → 127.0.0.1:4000)
└── README.md                 este arquivo
```

## Endpoints expostos (via nginx: prefixo `/api/` acrescentado externamente)

| Rota pública                        | Rota interna FastAPI          | Retorno                                                                          |
|-------------------------------------|-------------------------------|----------------------------------------------------------------------------------|
| `GET /api/health`                   | `/health`                     | `{ "status": "ok" }`                                                             |
| `GET /api/franchises`               | `/franchises`                 | `{ data: Franchise[], total, page, lastPage }`                                   |
| `GET /api/franchises/count`         | `/franchises/count`           | `{ total: number }`                                                              |
| `GET /api/franchises/{slug}`        | `/franchises/{slug}`          | `{ data: Franchise }` — com `contact`, `owner`, `businessModels`, `reviews`       |
| `GET /api/ranking`                  | `/ranking`                    | `{ data: Franchise[], total, page, lastPage }` — cada item tem `rankingPosition` |
| `POST /api/auth/login`              | `/auth/login`                 | `{ user: {id,email,name,role}, access_token }` — 404 em credenciais inválidas    |
| `POST /api/auth/validate`           | `/auth/validate`              | `{ valid, payload, message }` — header `Authorization: Bearer <jwt>`             |
| `POST /api/auth/forgot-password`    | `/auth/forgot-password`       | `{ message, expiresAt }` — 400 com `{expiresIn,message}` se há código ativo       |
| `POST /api/auth/verify-reset-code`  | `/auth/verify-reset-code`     | `{ message }` — 400 código inválido / 401 expirado                               |
| `POST /api/auth/reset-password`     | `/auth/reset-password`        | `{ message, user, access_token }` — auto-login após reset                        |
| `POST /api/auth/resend-reset-code`  | `/auth/resend-reset-code`     | `{ message, expiresAt }`                                                          |
| `POST /api/users/register/step-one`       | `/users/register/step-one`       | `{ user, access_token }` — cria conta (email/senha/nome/tel); 409 se duplicado |
| `POST /api/users/register/step-two`       | `/users/register/step-two`       | `{ message, user, access_token }` — role + perfil (city/sectors/region/investment); JWT obrigatório |
| `GET  /api/users/me`                      | `/users/me`                      | `User` hidratado (profile, franchisorProfile, franchiseeOf)                 |
| `PUT  /users/me`                          | `/users/me`                      | `{ user }` — atualiza nome/telefone/cpf; admin pode mexer `isActive`         |
| `PUT  /api/users/me/password`             | `/users/me/password`             | `{ message, user }` — troca senha                                           |
| `GET  /api/users/me/profile-completion`   | `/users/me/profile-completion`   | `{ isComplete, completionPercentage, missingFields[] }` — 9 campos pesam igual |
| `POST /api/users/me/request-email-change` | `/users/me/request-email-change` | `{ message, expiresAt }`; 400 `{expiresIn,message}` se código ativo; 409 se email em uso |
| `POST /api/users/me/verify-email-change`  | `/users/me/verify-email-change`  | `{ message, user }` — aplica troca                                          |
| `PUT  /api/users/profile`                 | `/users/profile`                 | `{ message, user?, access_token?, roleChanged }` — re-emite JWT se role mudou |
| `POST /api/users/franchisor-request`      | `/users/franchisor-request`      | multipart — cria solicitação PENDING + dois arquivos (cnpjCard, socialContract) |
| `GET  /api/users/franchisor-request/my-request` | `/users/franchisor-request/my-request` | `FranchisorRequest` ou `null`                                    |
| `GET  /api/news`                         | `/news`                                | `{ data, total, page, lastPage }` (ativas, filtros `search`, `category`) |
| `GET  /api/news/{id}`                    | `/news/{id}`                           | single news (404 se inativa/não existe)                           |
| `GET  /api/news/{id}/comments`           | `/news/{id}/comments`                  | array de comments com `author` embutido                           |
| `POST /api/news/{id}/comments`           | `/news/{id}/comments`                  | cria comentário (JWT; perfil completo obrigatório)               |
| `GET  /api/favorites`                    | `/favorites`                           | `{ data, meta:{total,page,limit,totalPages} }` — paginado        |
| `GET  /api/favorites/ids`                | `/favorites/ids`                       | `{ franchiseIds: string[] }`                                     |
| `GET  /api/favorites/check/{slug}`       | `/favorites/check/{slug}`              | `{ isFavorited: boolean }`                                       |
| `POST /api/favorites/{slug}`             | `/favorites/{slug}`                    | add; 201 `{success,message,data}`; 400 se franquia inativa       |
| `POST /api/favorites/{slug}/toggle`      | `/favorites/{slug}/toggle`             | `{ success, data:{isFavorited, message} }` — idempotente         |
| `DELETE /api/favorites/{slug}`           | `/favorites/{slug}`                    | `{ success, message }`                                           |
| `GET  /api/reviews/franchise/{slug}`     | `/reviews/franchise/{slug}`            | paginado `{ data, total, page, limit, lastPage }`                 |
| `GET  /api/reviews/franchise/franchisee/{slug}` | `/reviews/franchise/franchisee/{slug}` | `{ hasReviewed, reviewId, rating }` — JWT                         |
| `POST /api/reviews/{slug}`               | `/reviews/{slug}`                      | cria review; 400 se já avaliou; 403 se perfil incompleto; atualiza `reviewCount`/`ratingSum`/`averageRating` |
| `GET  /api/quiz`                         | `/quiz`                                | metadata da submissão do usuário ou `null`                        |
| `POST /api/quiz`                         | `/quiz`                                | upsert das respostas (JSON livre, campos-chave documentados)      |
| `GET  /api/quiz/profile`                 | `/quiz/profile`                        | `{ answers: [{key,label,value}] }` — 5 campos                     |
| `GET  /api/quiz/results`                 | `/quiz/results`                        | `{ hasSubmission, blocks:[{label,zone,pagination,franchises}] }` |
| `GET  /api/notifications`                | `/notifications`                       | paginado (`unreadOnly` bool)                                      |
| `GET  /api/notifications/stats`          | `/notifications/stats`                 | `{ total, unread, hasUnread }`                                    |
| `PATCH /api/notifications/mark-read`     | `/notifications/mark-read`             | body `{notificationIds[]}`; `{updated:N}`                         |
| `POST /api/notifications/mark-all-read`  | `/notifications/mark-all-read`         | `{updated:N}`                                                     |
| `PUT  /api/notifications/{id}/read`      | `/notifications/{id}/read`             | notificação serializada                                           |
| `DELETE /api/notifications/{id}`         | `/notifications/{id}`                  | `{success:true}`                                                  |

Filtros e ordenação do `/franchises` (todos opcionais, query string):

- paginação: `page`, `limit`
- busca: `search` (ilike em `name`)
- segmentação: `segment`, `subsegment`, `excludeSubsegment`
- faixas numéricas: `minInvestment`, `maxInvestment`, `minUnits`, `maxUnits`,
  `minROI`, `maxROI`, `minFranchiseFee`, `maxFranchiseFee`, `minRevenue`,
  `maxRevenue`, `minRating`, `maxRating`
- patrocinado: `isSponsored`
- sort (valores `asc` ou `desc`): `nameSort`, `ratingSort`, `unitsSort`,
  `investmentSort`, `roiSort`, `franchiseFeeSort`, `revenueSort`

Mesmos nomes de parâmetros usados em `web/src/services/franchises.ts` —
drop-in replacement do endpoint NestJS atual.

## 1. Envio ao EC2 (um comando do laptop)

```bash
scp -r \
  ~/Downloads/franchise_db_dump.sql \
  ~/Developer/mercadofranquia-site/deploy/ec2/app \
  ~/Developer/mercadofranquia-site/deploy/ec2/migrate.py \
  ~/Developer/mercadofranquia-site/deploy/ec2/mf-api.service \
  ~/Developer/mercadofranquia-site/deploy/ec2/mercadofranquia.nginx \
  ubuntu@18.230.68.207:~/
```

(Use `-i <key>` se precisar. `scp -r` copia a pasta `app/` inteira.)

## 2. No EC2

```bash
ssh ubuntu@18.230.68.207
```

### 2a. Conferir chegada

```bash
ls -lh ~/franchise_db_dump.sql ~/migrate.py ~/mf-api.service ~/mercadofranquia.nginx
ls ~/app ~/app/routers
grep -c '^INSERT INTO' ~/franchise_db_dump.sql   # 2878
```

### 2b. Dependências Python (única vez)

```bash
source ~/mf-api/bin/activate
pip install 'psycopg[binary]>=3.1' sqlparse 'sqlalchemy>=2.0' fastapi 'uvicorn[standard]' pyjwt bcrypt 'pydantic[email]' python-multipart
```

### 2c. Migração do banco (use psycopg URL plain — sem `+psycopg` — para o migrate)

```bash
# Dry-run:
python ~/migrate.py --dry-run | head -40

# Execução real:
python ~/migrate.py --db 'postgresql://mf_user:$DB_PASSWORD@localhost:5432/mercadofranquia'
```

Esperado:
```
-- Loading data --
-- Resetting sequences --
COMMIT OK.

=== Row counts (PostgreSQL) ===
  Franchise                  1404
  ContactInfo                1405
  ...
  TOTAL                      2878
```

### 2d. Instalar o pacote `app/` no projeto

```bash
rm -rf ~/mercadofranquia-api/app
cp -r ~/app ~/mercadofranquia-api/app
```

### 2e. Smoke-test manual

```bash
cd ~/mercadofranquia-api
export DATABASE_URL='postgresql+psycopg://mf_user:$DB_PASSWORD@localhost:5432/mercadofranquia'
uvicorn app.main:app --host 127.0.0.1 --port 4000 &
sleep 3
curl -s http://127.0.0.1:4000/health
curl -s http://127.0.0.1:4000/franchises/count
curl -s 'http://127.0.0.1:4000/ranking?limit=3' | head -c 800
kill %1
```

Esperado respectivamente: `{"status":"ok"}`, `{"total":1403}`, JSON com 3
franquias em ordem decrescente por `totalUnits`.

### 2f. systemd

```bash
sudo cp ~/mf-api.service /etc/systemd/system/mf-api.service
sudo systemctl daemon-reload
sudo systemctl enable mf-api
sudo systemctl start mf-api
sudo systemctl status mf-api --no-pager
sudo journalctl -u mf-api -n 30 --no-pager
curl -s http://127.0.0.1:4000/health
```

> A `mf-api.service` já seta `DATABASE_URL` com `postgresql+psycopg://`
> (driver psycopg 3, ideal para SQLAlchemy 2).

### 2g. Nginx

```bash
sudo cp ~/mercadofranquia.nginx /etc/nginx/sites-available/mercadofranquia
sudo ln -sf /etc/nginx/sites-available/mercadofranquia /etc/nginx/sites-enabled/mercadofranquia
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 2h. Testes externos (do laptop)

```bash
curl -s http://18.230.68.207/api/health
curl -s http://18.230.68.207/api/franchises/count
curl -s 'http://18.230.68.207/api/ranking?limit=3'
curl -s 'http://18.230.68.207/api/franchises?search=cacau'
curl -s 'http://18.230.68.207/api/franchises/cacau-show'
```

## CORS

`app/main.py` libera `*` por default. Para restringir (recomendado antes de
ir para produção), exportar:

```
CORS_ORIGINS=https://mercadofranquia.vercel.app,https://mercadofranquia.com.br
```

Pode ser colocado dentro do unit systemd em `Environment=`.

## Auth — variáveis de ambiente obrigatórias

| Var | Valor atual | Origem |
|---|---|---|
| `JWT_SECRET`     | **inline no `mf-api.service`** (gere com `python3 -c "import secrets; print(secrets.token_hex(32))"`) |
| `JWT_EXPIRES_IN` | `1h`                                                                |
| `BCRYPT_ROUNDS`  | `10` (hardcoded em `security.py`; bate com hashes `$2b$10$...` existentes) |

O secret **deve ser o mesmo** usado pelo NestJS enquanto os dois backends
convivem (senão tokens emitidos por um não são validados pelo outro). Quando
retirar o NestJS do ar, rotacione o secret e os usuários precisarão logar de
novo. **Nunca comitar o secret em doc ou Git** — vive só no unit e em
`api/.env` (ambos `gitignored`).

**Reset de senha — stub de e-mail:** nenhum SMTP configurado ainda. O código
de 6 dígitos vai pro log do systemd:

```bash
sudo journalctl -u mf-api -f | grep 'RESET CODE'
# [RESET CODE] to=user@example.com name=Fulano code=438291 expires_at=... (email not actually sent — stub)
```

Pra plugar SMTP de verdade: trocar a função `_dispatch_reset_email` em
`app/routers/auth.py` por uma chamada pro seu provider (SES, SendGrid,
Mailgun, SMTP direto).

## Verificações locais já feitas antes do deploy

- `migrate.py` rodou contra `postgres:15-alpine` local — 2.878 linhas, 20
  tabelas, 35 índices, FKs íntegras, booleanos e JSONB preservados,
  sequências resetadas.
- `uvicorn app.main:app` rodou contra o mesmo DB seedado:
  - `GET /health` → 200.
  - `GET /franchises/count` → `{"total": 1403}`.
  - `GET /franchises/count?segment=aliment` → `{"total": 369}`.
  - `GET /franchises?unitsSort=desc&limit=3` → Cacau Show (4.661) / O Boticário (4.051) / McDonald's (2.779).
  - `GET /franchises?investmentSort=asc&limit=3` → FIADORWEB R$1.500 / DEUTSCHIPS R$2.500 / CASTOR R$4.000.
  - `GET /franchises?search=cacau` → 2 resultados (Cacau Show, Chocolates Brasil Cacau).
  - `GET /franchises/cacau-show` → campos completos, `sponsorPlacements` como array real (`["RANKING_CATEGORIA","QUIZ","HOME_DESTAQUES"]`), contato/owner/businessModels/reviews carregados via `selectinload`.
  - `GET /ranking?limit=3` → total 1.403, itens com `rankingPosition` 1..3.
  - CORS preflight (`OPTIONS /franchises`) → 200 com `access-control-allow-origin: *`.
- `app/routers/auth.py` testado end-to-end contra DB seedado (usuário de teste
  inserido manualmente):
  - `POST /auth/login` com senha certa → 200 `{user, access_token}`.
  - `POST /auth/login` com senha errada / e-mail inexistente → 404 (privacy).
  - `POST /auth/validate` com header válido → 200 `{valid, payload, message}`.
  - `POST /auth/validate` sem header → 401 "Invalid Authorization header format".
  - `POST /auth/validate` com token corrompido → 401 "Invalid or expired token".
  - `POST /auth/forgot-password` (e-mail válido) → 200 `{message, expiresAt}`; código logado.
  - Segundo `forgot-password` dentro da janela → 400 `{expiresIn, message}`.
  - `forgot-password` com e-mail desconhecido → 404 (frontend trata como sucesso).
  - `POST /auth/verify-reset-code` com código válido → 200; código errado → 400.
  - `POST /auth/reset-password` com código válido → 200 com auto-login; reuso do mesmo código → 400; senha antiga inválida pós-reset.
  - `POST /auth/resend-reset-code` sem registro prévio → 400.
  - JWT emitido pelo FastAPI é verificado corretamente pelo próprio FastAPI
    (mesmo payload shape que NestJS: `{id,email,name,role,isActive,iat,exp}`).
- `app/routers/{register,users,franchisor_requests}.py` testados end-to-end
  contra DB seedado, 19 casos verdes:
  - `register/step-one` ok + duplicate-email → 409.
  - `users/me` GET + PUT (name/cpf), validação de CPF modulo-11, `cpf` único.
  - `users/me/password` PUT.
  - `profile-completion` varia de 33% (só basic info) → 100% após step-two.
  - `register/step-two` CANDIDATE ok + segundo chamado → 409.
  - `users/profile` com role change emite novo `access_token` e `roleChanged=true`;
    sem role change retorna `roleChanged=false` sem token novo.
  - `request-email-change` ok + dentro da janela → 400 rate-limit + mesmo e-mail
    atual → 400.
  - `franchisor-request` multipart (CNPJ validado pelo algoritmo modulo-11,
    arquivos salvos em `uploads/franchisor-requests/<user>/<slot>-<hash>.ext`),
    `my-request` lê de volta, POST duplicado → 409.
  - Endpoints protegidos sem header → 401.
- `app/routers/{news,favorites,reviews,quiz,notifications}.py` — 42 asserções
  verdes contra DB seedado (fixtures manuais para `News` e `Notification`,
  já que o dump tem essas tabelas vazias):
  - News: paginação/search/category, active-only gate (404 em inativa),
    comentários read público, comentário write com profile-complete gate.
  - Favorites: check/add/remove/toggle idempotentes, `favoritesCount`
    aumenta e decrementa, `ids` sincroniza, paginação funciona.
  - Reviews: create com checagem de `isFranchisee` via relação M2M,
    duplicate-prevention 400, `averageRating`/`ratingSum`/`reviewCount`
    do `Franchise` atualizados transacionalmente, has-reviewed check.
  - Quiz: upsert POST, profile summary com 5 campos, results retornou
    **338 franquias ranqueadas** em ZONE_1+ZONE_2 para perfil Alice
    (capital 100k-300k, segmentos Alimentação/Saúde).
  - Notifications: list/stats/single-mark/bulk-mark/mark-all/delete, filtro
    `unreadOnly`, `hasUnread` reflete corretamente, idempotência em
    mark-all-read quando tudo já lido.

### Quiz scoring caveat

O algoritmo em `app/routers/quiz.py` é uma **versão simplificada** do
`QuizScoringService` do NestJS. Usa 5 dimensões (segment, investment,
payback, revenue, network) com pesos fixos (0.30/0.30/0.15/0.15/0.10)
e zoneamento por múltiplos da faixa de capital. Dá resultados plausíveis
mas não bate 1:1 com o backend Node. Portar fielmente é uma próxima tarefa
(~300 linhas de TS do `quiz-scoring.service.ts`).

## HTTPS (quando tiver domínio apontado)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d mercadofranquia.com.br -d www.mercadofranquia.com.br
```

## Troubleshooting

| Sintoma                                    | Onde olhar                                                                 |
|--------------------------------------------|----------------------------------------------------------------------------|
| `500` em `/api/*`                          | `sudo journalctl -u mf-api -e`                                             |
| `502 Bad Gateway` do nginx                 | API não está em 4000. `ss -ltnp \| grep 4000`. `systemctl status mf-api`   |
| `ModuleNotFoundError: psycopg`             | Deps faltando no venv. Rode 2b.                                            |
| `missing "=" after "postgresql+psycopg"`   | `migrate.py` usa libpq; passar URL sem `+psycopg`. Ver 2c.                 |
| `postgresql+psycopg` rejeitado             | SQLAlchemy < 2.0 ou psycopg 3 não instalado.                                |
| CORS bloqueia chamada do front             | Exportar `CORS_ORIGINS` no unit systemd + `systemctl restart mf-api`.       |
| Queries lentas                             | Índices criados pelo `migrate.py` (35). Verificar `EXPLAIN ANALYZE`.       |

## Rollback do banco

```bash
sudo -u postgres psql -c 'DROP DATABASE mercadofranquia;'
sudo -u postgres psql -c 'CREATE DATABASE mercadofranquia OWNER mf_user;'
python ~/migrate.py --db 'postgresql://mf_user:$DB_PASSWORD@localhost:5432/mercadofranquia'
```

## Próximos passos previstos

- Apontar o frontend (Next.js) para `NEXT_PUBLIC_API_URL=http://18.230.68.207`
  (ou o domínio com TLS depois). Já consome `/api/franchises` e
  `/api/franchises/{slug}` no formato que os routers retornam, então a
  troca é só de variável de ambiente.
- Adicionar endpoints `/api/news`, `/api/users`, `/api/quiz` conforme o
  front for migrando do NestJS atual.
- Autenticação JWT — só preciso quando for habilitar os painéis admin
  via esta API.
