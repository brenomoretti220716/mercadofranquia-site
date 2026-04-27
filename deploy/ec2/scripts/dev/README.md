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

Seed canonico de `pizza-do-joao` alinhado com o mockup
`docs/mockups/pagina_publica_franquia_v10_handoff.html`. Idempotente.

O que popula:

1. **Franchise (UPDATE):** tagline, description, segment "Alimentação",
   franchiseStartYear 2014, headquarter "São Paulo, SP", totalUnits 62,
   minimumInvestment 139000 / maximumInvestment 342000 (em REAIS), payback
   22 meses, processSteps (3 etapas) e differentials (4 itens) JSONB,
   idealFranchiseeProfile, galleryUrls (4 placeholders).
2. **Status:** PENDING -> APPROVED (necessario pro endpoint publico).
3. **BusinessModels:** 3 cards (Loja, Container, Quiosque) com lookup
   por (franchiseId, name) — sem duplicar.
4. **Reviews:** so se reviewCount=0, cria 4 + 1 ReviewResponse com perfis
   do mockup (rating 5 payback, 4 capital de giro, 5 anonima
   transparencia, 3 critica suporte).
5. **Counters denormalizados:** reviewCount, averageRating, ratingSum.
