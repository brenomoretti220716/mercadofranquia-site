# Scripts de migracao — arquivados

Estes scripts cumpriram seu papel e **nao devem ser executados novamente**.
Foram preservados aqui como referencia historica do processo de migracao.

## Contexto

- **migrate.py** — migracao MySQL -> PostgreSQL, executada em 17/abr/2026
  durante a transicao do stack antigo (NestJS + MySQL) para o atual
  (FastAPI + PostgreSQL). Leu dump `franchise_db_dump.sql` e populou
  as 20 tabelas PascalCase do Postgres.

- **migrate_sqlite_to_pg.py** — ETL one-shot do pipeline de inteligencia
  (SQLite `abf.db`) para o Postgres. ~10k linhas em 9 tabelas,
  idempotente via `ON CONFLICT` nas UniqueConstraints.

## Por que nao executar de novo

1. **Os dados ja estao no Postgres.** Rerodar iria apagar e recriar tabelas.
2. **As fontes originais foram arquivadas** (`~/Archive/...` no dev env, fora do repo).
3. **Ambos contem senha antiga hardcoded** como `DEFAULT_DB_URL`.
   Como sao scripts arquivados, a senha (ja rotacionada) nao foi sanitizada.

## Se um dia precisar de ideia de uma migracao parecida

Use como **referencia conceitual**, nao como codigo executavel. Reescrever
para o contexto novo custa menos do que adaptar estes.
