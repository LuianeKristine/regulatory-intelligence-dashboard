# Validation Checklist

Use this checklist before a client demo or production publish.

## Cloudflare Runtime

- [ ] Worker deployado
- [ ] D1 conectado
- [ ] KV configurado ou Cache API validado
- [ ] Cron trigger configurado
- [ ] Variaveis `CACHE_TTL_SECONDS` e `CORS_ORIGIN` revisadas
- [ ] `CRON_SECRET` configurado se o endpoint interno for exposto

## API

- [ ] `GET /api/health` funcionando
- [ ] `POST /api/sync` funcionando
- [ ] `GET /api/stats` retornando metricas
- [ ] `GET /api/guidances` retornando documentos
- [ ] `GET /api/press` retornando press announcements
- [ ] `GET /api/approvals` retornando approvals
- [ ] `GET /api/documents/:id` retornando detalhe e versoes
- [ ] Respostas de erro seguem `{ success: false, error: { message, code } }`

## FDA Data

- [ ] Dados reais FDA aparecendo
- [ ] Links oficiais FDA abrindo corretamente
- [ ] Links PDF abrindo corretamente quando existirem
- [ ] Novos documentos marcados como `NEW`
- [ ] Documentos alterados marcados como `UPDATED`
- [ ] Historico em `document_versions` criado para novos/atualizados
- [ ] Fallback de erro funcionando quando FDA falha ou bloqueia temporariamente

## Dashboard

- [ ] Dashboard responsiva em desktop
- [ ] Dashboard responsiva em mobile
- [ ] Overview renderiza metricas e atividade recente
- [ ] Busca textual funcionando
- [ ] Filtro por fonte funcionando
- [ ] Filtro por FDA center funcionando
- [ ] Filtro por status funcionando
- [ ] Filtro por data funcionando
- [ ] Filtros `New` e `Updated` funcionando
- [ ] Ordenacao por data funcionando
- [ ] Paginacao funcionando
- [ ] Estado vazio funcionando
- [ ] Estado de loading funcionando
- [ ] Estado de erro funcionando
- [ ] Painel lateral de detalhe abre e fecha corretamente

## Demo Readiness

- [ ] Sync manual executado antes da demo
- [ ] Ultimo sync aparece no Overview
- [ ] Fontes planejadas aparecem como placeholders
- [ ] Settings permite apontar para a URL do Worker
- [ ] README atualizado com comandos corretos do projeto
