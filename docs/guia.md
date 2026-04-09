# Guia para rodar na aws(EC2)

### 1) Envs necessários (defina manualmente) no diretório clonado.

```env
JWT_SECRET=troque_por_uma_chave_forte
GROQ_API_KEY=troque_pela_sua_chave
MYSQL_ROOT_PASSWORD=troque_por_root_forte
MYSQL_PASSWORD=troque_por_senha_forte
NEXT_PUBLIC_API_URL=http://localhost:4000

# Banco e Redis (a URL mysql://... e montada no docker-compose a partir destas keys)
MYSQL_DATABASE=franchise_db
MYSQL_USER=franchise_user
REDIS_PASSWORD=sua_senha

# SMTP (necessario para envio de email funcionar)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=seu_email@gmail.com
SMTP_PASS=sua_senha_ou_app_password
SMTP_FROM="Sistema de Franquias <seu_email@gmail.com>"
```

Nao defina `DATABASE_URL` no `.env` com `${MYSQL_PASSWORD}` dentro da string: o Compose pode nao interpolar e o Prisma falha ao conectar. Use `MYSQL_USER`, `MYSQL_PASSWORD` e `MYSQL_DATABASE` como acima.

### 2) Comandos para rodar

```bash
docker compose up -d --build

# logs
docker compose logs -f api web
```

O `docker compose up` ja executa automaticamente `npx prisma db push` (servico `prisma-db-push`) e, em seguida, o servico `mysql-import`.

### Importacao opcional do dump MySQL

- Coloque o arquivo `.sql` no host (por padrao o compose espera `./api/dump-dados-20260408.sql`).
- Apos o schema existir, o script conta linhas na tabela `User` (configuravel). Se `COUNT > 0`, **nao importa de novo**.
- Variaveis opcionais no `.env`:
  - `MYSQL_DUMP_HOST_PATH` — caminho do arquivo `.sql` no host (default `./api/dump-dados-20260408.sql`).
  - `MYSQL_SEED_CHECK_TABLE` — tabela usada para decidir se ja ha dados (default `User`).
  - `SKIP_MYSQL_IMPORT=1` — nunca importa o dump.

Se o arquivo de dump nao existir ou estiver vazio, o import e ignorado sem erro.
