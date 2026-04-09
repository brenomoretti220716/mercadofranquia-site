# Guia para rodar na AWS (EC2)

## Primeiros passos: clonar e configurar o `.env`

### 1) Clonar o repositório

```bash
git clone https://github.com/brenomoretti220716/mercadofranquia-site.git
cd mercadofranquia-site
```

### 2) Criar o `.env` na raiz do projeto

O `docker compose` lê o arquivo `**.env` no diretório onde você roda o comando** (a raiz do clone). Crie esse arquivo e preencha as variáveis necessárias (senhas, URLs públicas da API, etc.).

---

### 3) Variáveis necessárias (defina manualmente no `.env` da raiz)

```env
JWT_SECRET=troque_por_uma_chave_forte
GROQ_API_KEY=troque_pela_sua_chave
MYSQL_ROOT_PASSWORD=troque_por_root_forte
MYSQL_PASSWORD=troque_por_senha_forte
NEXT_PUBLIC_API_URL=http://localhost:4000

# Banco e Redis (a URL mysql://... é montada no docker-compose a partir destas keys)
MYSQL_DATABASE=franchise_db
MYSQL_USER=franchise_user
REDIS_PASSWORD=sua_senha

# SMTP (necessário para envio de e-mail funcionar)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=seu_email@gmail.com
SMTP_PASS=sua_senha_ou_app_password
SMTP_FROM="Sistema de Franquias <seu_email@gmail.com>"
```

### 4) Comando para rodar

```bash
docker compose up -d --build
```

