# Data Quality Checklist

Use this checklist when validating a source parser or preparing a client demo.

## Multi-level Scraping

- [ ] O scraper entra na pagina interna do produto?
- [ ] O scraper entra na pagina interna do guidance quando houver link oficial?
- [ ] O scraper normaliza URLs relativas para URLs absolutas FDA?
- [ ] O scraper captura links `/media/.../download`?
- [ ] O scraper captura PDFs diretos?
- [ ] O scraper classifica documentos relacionados por tipo?
- [ ] O sync nao quebra se a FDA bloquear, falhar ou mudar HTML?
- [ ] O fallback mostra ultimo dado salvo quando a FDA falha?

## Required Supporting Documents

- [ ] Captura Package Insert?
- [ ] Captura Approval Letter?
- [ ] Captura Clinical Review?
- [ ] Captura Statistical Review?
- [ ] Captura Summary Basis for Regulatory Action / SBRA?
- [ ] Captura Prescribing Information?
- [ ] Captura Label?
- [ ] Captura FDA Review?
- [ ] Nao mostra PDF como unavailable quando ha PDF ou `/media/.../download`?

## UI Quality

- [ ] Nao mostra JSON bruto?
- [ ] Nao mostra `metadata_json` cru?
- [ ] Nao mostra `content_hash`?
- [ ] Nao mostra `raw_text_snapshot`?
- [ ] Nao mostra internal IDs?
- [ ] Nao mostra valores `null`?
- [ ] Nao mostra valores `undefined`?
- [ ] Campos vazios aparecem como `Not identified` ou sao ocultados?
- [ ] Pagina FDA original abre corretamente?
- [ ] PDF abre corretamente?

## RYONCIL Manual Validation

FDA page:

```text
https://www.fda.gov/vaccines-blood-biologics/cellular-gene-therapy-products/ryoncil
```

Confirmar que o sistema extrai:

- [ ] Proper Name: `remestemcel-L-rknd`
- [ ] Tradename: `RYONCIL`
- [ ] Manufacturer/Sponsor: `Mesoblast, Inc.`
- [ ] Indication: treatment of steroid-refractory acute graft versus host disease in pediatric patients 2 months of age and older
- [ ] Package Insert link
- [ ] Approval Letter link
- [ ] Clinical Review Memo link
- [ ] Summary Basis for Regulatory Action link
- [ ] Approval History / related documents link

If any field is not found:

- [ ] Worker logs a structured warning
- [ ] UI stays usable
- [ ] UI displays `Not identified` or a friendly empty state
