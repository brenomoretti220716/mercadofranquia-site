# scripts/dev/

Utilitarios de desenvolvimento local — **nao** sao migrations e **nao** rodam em produ&ccedil;ao.

Migrations canonicas vivem em `deploy/ec2/migrations/` e sao gerenciadas via
Alembic. Tudo aqui em `scripts/dev/` e idempotente, focado em popular dados
de teste pra validar features visualmente em `localhost:3000`.

## Convencoes

- Cada script deve ser idempotente (re-rodar nao duplica dados).
- Cada script deve usar `DATABASE_URL` via env (nao hardcode).
- Hashes de senha sao invalidos por design — usuarios criados aqui nao
  conseguem fazer login real.
- Scripts comecam com `seed_` quando inserem dados; outros prefixos
  conforme o caso (`reset_`, `purge_`, etc.).

## Como rodar

Ative o venv do projeto e exporte a URL do DB local:

```bash
DATABASE_URL=postgresql://mf_user:dev_password_local@localhost:5432/mercadofranquia \
  ~/Developer/mercadofranquia/.venv/bin/python \
  deploy/ec2/scripts/dev/<nome_do_script>.py
```

## Scripts disponiveis

### `seed_reviews_pizza_joao.py`

Aprova `pizza-do-joao` (status PENDING -> APPROVED) e garante 4 reviews + 1
ReviewResponse alinhados com o mockup `pagina_publica_franquia_v10_handoff.html`.

Reviews: rating 5 (payback rapido), rating 4 (capital de giro), rating 5
anonima (transparencia), rating 3 (suporte). Datas: 12, 28, 41, 60 dias atras.
Response na review rating 5 mais recente.

Idempotente — se ja houver reviews, apenas refresh dos counters denormalizados.
