# RegAI Real-Time

Dashboard regulatoria serverless para monitorar fontes reais da FDA, detectar novos documentos e mudancas por hash, armazenar dados no Cloudflare D1 e exibir tudo em uma interface estatica publicada no Cloudflare Pages.

Este MVP nao usa OpenAI, Anthropic, Gemini ou qualquer API paga de IA. A pasta `worker/src/services/aiAnalysis.ts` deixa a arquitetura preparada para uma fase futura.

## Arquitetura

```text
reg-ai-realtime/
  public/
    index.html
    styles.css
    app.js
    _headers

  worker/
    src/
      index.ts
      routes/
        advisory.ts
        approvals.ts
        documents.ts
        guidances.ts
        press.ts
        stats.ts
        sync.ts
      services/
        aiAnalysis.ts
        cache.ts
        fdaClient.ts
        hash.ts
        parser.ts
        syncService.ts
      db/
        schema.sql
        queries.ts
      types/
        index.ts
    wrangler.toml
    package.json
    tsconfig.json
```

## Fontes FDA do MVP

- FDA Guidance Documents: `https://www.fda.gov/regulatory-information/search-fda-guidance-documents`
- FDA Press Announcements: `https://www.fda.gov/news-events/fda-newsroom/press-announcements`
- Approved Cellular and Gene Therapy Products: `https://www.fda.gov/vaccines-blood-biologics/cellular-gene-therapy-products/approved-cellular-and-gene-therapy-products`

As fontes de fase 2 ja tem placeholders: advisory committees, OCE publications, OTP events e OTP learn.

## API

- `GET /api/health`
- `GET /api/guidances`
- `GET /api/guidances/:id`
- `GET /api/press`
- `GET /api/press/:id`
- `GET /api/approvals`
- `GET /api/approvals/:id`
- `GET /api/stats`
- `POST /api/sync`
- `POST /api/cron/sync`
- `GET /api/documents/:id` para o painel de detalhe da dashboard
- `GET /api/documents/:id/supporting-documents`

Filtros aceitos nas listas:

```text
q, source_type, fda_center, status, from, to, is_new, is_updated, limit, offset
```

## Requisitos

- Conta Cloudflare
- Node.js 20+
- Wrangler CLI

Instale o Wrangler:

```bash
npm install -g wrangler
wrangler login
```

## Configuracao do Worker

```bash
cd worker
npm install
npx wrangler d1 create regai-db
npx wrangler kv namespace create FDA_CACHE
npx wrangler kv namespace create FDA_CACHE --preview
```

Copie os IDs retornados para `worker/wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "regai-db"
database_id = "REPLACE_WITH_D1_DATABASE_ID"

[[kv_namespaces]]
binding = "FDA_CACHE"
id = "REPLACE_WITH_KV_NAMESPACE_ID"
preview_id = "REPLACE_WITH_PREVIEW_KV_NAMESPACE_ID"
```

Crie as tabelas no D1 remoto:

```bash
npx wrangler d1 execute regai-db --file=./src/db/schema.sql
```

Para ambiente local:

```bash
npx wrangler d1 execute regai-db --file=./src/db/schema.sql --local
npx wrangler dev
```

## Variaveis

Configuradas em `wrangler.toml`:

```toml
[vars]
CACHE_TTL_SECONDS = "900"
CORS_ORIGIN = "*"
```

Opcional para proteger o endpoint interno:

```bash
npx wrangler secret put CRON_SECRET
```

Se `CRON_SECRET` estiver definido, chame `POST /api/cron/sync` com header `X-Cron-Secret`.

## Deploy do Worker

```bash
cd worker
npm install
npx wrangler deploy
```

Depois do deploy, rode uma sincronizacao manual:

```bash
curl -X POST https://YOUR_WORKER.YOUR_SUBDOMAIN.workers.dev/api/sync
```

Teste saude e dados:

```bash
curl https://YOUR_WORKER.YOUR_SUBDOMAIN.workers.dev/api/health
curl https://YOUR_WORKER.YOUR_SUBDOMAIN.workers.dev/api/guidances
curl https://YOUR_WORKER.YOUR_SUBDOMAIN.workers.dev/api/stats
```

## Cron Trigger

O `wrangler.toml` ja inclui:

```toml
[triggers]
crons = ["*/30 * * * *"]
```

Isso executa sync automatico a cada 30 minutos apos o deploy do Worker.

## Deploy do Frontend no Cloudflare Pages

O frontend fica em `public/` e nao precisa de build.

Opcao com Wrangler:

```bash
npx wrangler pages deploy public --project-name regai-realtime
```

Opcao pelo painel Cloudflare Pages:

1. Crie um projeto Pages.
2. Configure o diretorio de output como `public`.
3. Publique.
4. Abra a dashboard e preencha o campo `API` com a URL do Worker.

Se voce publicar Worker e Pages no mesmo dominio com rota/proxy, o campo `API` pode ficar vazio e a dashboard usara o mesmo origin.

## Como funciona a deteccao

1. O Worker busca as fontes FDA com cache de 15 minutos por padrao.
2. O parser normaliza titulo, URL, PDF, centro FDA, status, topico e datas quando disponiveis.
3. O Worker entra na pagina interna de cada item para descobrir metadados e documentos relacionados.
4. `documentDiscovery.ts` classifica links como Package Insert, Approval Letter, Clinical Review, SBRA e outros documentos de suporte.
5. O hash SHA256 e calculado sobre o conteudo relevante normalizado, incluindo documentos de suporte.
6. O ID estavel vem de `source_type + URL`.
7. Se o documento nao existe no D1, ele e inserido como `is_new = true`.
8. Se existe e o hash mudou, ele e marcado como `is_updated = true` e recebe uma linha em `document_versions`.
9. Se existe e o hash nao mudou, apenas `last_checked_at` e atualizado.

## Supporting Documents

O banco inclui a tabela `supporting_documents`, relacionada a `documents.id`.

O Worker procura:

- Package Insert
- Approval Letter
- Clinical Review
- Statistical Review
- Summary Basis for Regulatory Action / SBRA
- Prescribing Information
- Label
- FDA Review
- Briefing documents, presentations, transcripts, agendas e questions quando aplicavel

Endpoints de detalhe retornam:

```json
{
  "document": {},
  "supporting_documents": [],
  "versions": [],
  "metadata": {}
}
```

Tambem existe:

```text
GET /api/documents/:id/supporting-documents
```

Na UI, esses dados sao exibidos como cards regulatórios amigaveis. JSON bruto, hashes e campos internos nao devem aparecer para usuarios finais.

## Cache e fallback

- KV e usado quando o binding `FDA_CACHE` existe.
- Sem KV, o Worker usa Cache API.
- Se a FDA falhar durante sync, os dados antigos continuam no D1 e a dashboard segue lendo o ultimo estado salvo.

## Limitacoes do plano gratuito

- Workers tem limite de CPU por requisicao.
- D1 e KV possuem limites diarios no plano gratuito.
- A FDA pode alterar HTML, DataTables ou aplicar bloqueios temporarios.
- O parser de guidances tenta JSON primeiro e usa fallback HTML quando necessario.
- Press announcements sao lidos das primeiras paginas recentes para reduzir custo.

## IA futura

O arquivo `worker/src/services/aiAnalysis.ts` define a interface:

```ts
export interface AIAnalysisResult {
  executiveSummary: string[];
  keyPoints: string[];
  regulatoryImpact: string;
  impactLevel: "low" | "medium" | "high";
}
```

Na fase 2, adicione um provider pago ou open source atras dessa interface, crie uma tabela de analises se necessario e dispare a analise apenas para documentos novos ou atualizados.

## Next Steps

1. Validar scraping das fontes FDA
2. Melhorar parsers por fonte
3. Adicionar Advisory Committees completos
4. Adicionar OCE Publications
5. Adicionar sistema de classificacao de impacto
6. Adicionar modulo de IA futura
7. Adicionar autenticacao se necessario
8. Adicionar exportacao CSV/PDF
9. Adicionar alertas por e-mail futuramente
10. Preparar demo para cliente
