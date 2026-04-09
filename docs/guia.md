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

O `docker compose up` ja executa automaticamente `npx prisma db push` (servico `prisma-db-push`) antes de subir a API.
