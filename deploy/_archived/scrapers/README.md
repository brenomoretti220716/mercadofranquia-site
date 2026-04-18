# Scrapers arquivados

Scripts Node.js legados, movidos aqui em 2026-04-18 durante a Fase 0 da fusão Intelligence → Site.

## Por que foram arquivados

Todos usam **MySQL local** (`franchise_db`) que não existe mais — o site
migrou pra **PostgreSQL no EC2**. Rodar qualquer um desses scripts como
está falha na conexão do banco.

Contêm também credenciais MySQL hardcoded (obsoletas).

## Scripts

- `scraper-logos-favicon.js` — backfill de logos via og:image + Google Favicon API
- `scraper-logos-html.js` — fallback por scraping HTML do site da franquia
- `scraper-mindconsulting.js` — sync da API legada apifranchise.mindconsulting.com.br

## Se um dia reaproveitar

A lógica é útil mas o código precisa ser **reescrito** em Python (FastAPI)
contra o PostgreSQL atual. Não rodar como está.
