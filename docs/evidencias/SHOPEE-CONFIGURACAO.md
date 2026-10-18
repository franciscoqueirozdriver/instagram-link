# Evidência — cofre de credenciais Shopee

Data: 17/10/2026.

## Implementado

- Tabela `instagram_link.shopee_organization_credentials` com `organization_id` como chave, ciphertext, autor e datas.
- RLS habilitado; grants para `PUBLIC`, `anon` e `authenticated` revogados.
- API administrativa para estado e substituição do par App ID/App Secret. A resposta retorna somente estado/datas; App Secret é `writeOnly` no OpenAPI.
- Cockpit: **Contas Instagram → Integração Shopee**, visível apenas ao Admin. Campos são limpos após salvar; valores antigos não são retornados. O Operador não pode ler ou escrever por essas rotas.
- Cifra Fernet reutiliza `TOKEN_ENCRYPTION_KEY`; nenhuma chave foi regenerada.
- Credenciais são vinculadas à organização, sem variáveis globais Shopee e sem inclusão em `.env.local`.

## Estado do banco e validação

- Antes da migration, conexão Supabase confirmada; migrations 001–006 registradas; tabela Shopee ausente.
- Migration 007 aplicada pelo runner do projeto: `db/migrations/007_shopee_organization_credentials.sql`.
- `scripts/verify_supabase.py`: passou; 16 tabelas no schema privado com RLS, sem acesso `anon`/`authenticated`; teste de cifra sintético revertido; Supabase Auth rejeitou token inválido; envios pausados.
- Nenhuma credencial Shopee foi gravada e nenhuma chamada à API Shopee foi feita.
- Testes: `tests/test_shopee_credentials.py` e `tests/test_config.py`: 5 passaram. `node --check` dos scripts de cockpit, `compileall`, parse do OpenAPI JSON e parse sintático do YAML passaram.
- Suíte completa: `timeout 90s .venv/bin/python -m pytest -q` expirou sem completar nem emitir resultado. `TEST_DATABASE_URL` está ausente; testes de integração PostgreSQL descartável não foram validados.

## Limite de integração

O Explorer oficial Shopee Affiliate Open API pede App ID e Secret, mas não disponibilizou o schema sem credenciais. Busca, ordenação, popularidade/vendas, comissão, detalhes, paginação, limites, assinatura, geração/atribuição de link e regras de imagens/cache seguem não confirmados. A integração ainda não busca produtos nem gera links. Não foi feito scraping, mock exibido como real, OAuth Meta ou envio de DM.

## Como cadastrar localmente

Com a API local em execução, o Administrador abre `http://127.0.0.1:8000/m0/connect#connections`, entra no cockpit e usa **Contas Instagram → Integração Shopee**. Instruções completas em [docs/21-INTEGRACAO-SHOPEE.md](../21-INTEGRACAO-SHOPEE.md). Credenciais devem ser obtidas do Explorer oficial e inseridas somente nesse formulário local, nunca no chat.
