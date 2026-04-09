# Importar o dump parcial no MySQL (cliente)

O ficheiro `.sql` gerado por `npm run export-dump:mysql` contém apenas **dados** (`INSERT`), não cria tabelas. O schema deve existir antes da importação.

## Passos

1. **Criar a base de dados** vazia no MySQL do cliente (ou usar uma base já criada).

2. **Aplicar o schema Prisma** (migrations), a partir da raiz do projeto, com `DATABASE_URL` a apontar para essa base:

   ```bash
   npx prisma migrate deploy
   ```

3. **Importar o ficheiro SQL** gerado (use o nome real do ficheiro, por exemplo `dump-dados-20260408.sql`):

   ```bash
   mysql -u USUARIO -p NOME_DA_BASE < dump-dados-20260408.sql
   ```

O próprio ficheiro `.sql` inclui um cabeçalho com `SET NAMES utf8mb4` e `FOREIGN_KEY_CHECKS` para facilitar a importação.

**Reimportar / base já com dados:** `PlatformStatistics` usa `REPLACE INTO` (uma linha com `id = 1`) para não falhar com “Duplicate entry” se essa linha já existir. Para o resto, um segundo `mysql < dump.sql` completo ainda pode falhar por chaves duplicadas em `User`, `Franchise`, etc.; nesse caso use uma base vazia ou apague as tabelas relevantes antes.

## Conteúdo do dump

**Dados de mercado (referência, sem FK para utilizadores/franquias):**

- `PlatformStatistics` — estatísticas agregadas da plataforma (`REPLACE INTO` no dump gerado)  
- `AbfSegmentEntry` — segmentos ABF (ano, trimestre, valores em R$ MM, etc.)  
- `RankingBugnumber` — cartões do ranking de grandes números (modelo Prisma `RankingBigNumber`)

**Restante:**

- `ContactInfo` referenciados por franquias exportadas  
- `User` com `role = ADMIN` (passwords em hash, para login continuar a funcionar)  
- Todas as linhas de `Franchise`, com `logoUrl`, `thumbnailUrl` e `galleryUrls` a `NULL` no ficheiro (a base de origem não é alterada)

Se `Franchise.ownerId` apontar para um utilizador que não é admin, o MySQL importa na mesma com `FOREIGN_KEY_CHECKS=0`; pode ser necessário corrigir dados na app conforme o caso.
