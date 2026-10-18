# Contratos da aplicação e fronteiras externas

> Atualização de escopo (16/10/2026): configuração por variáveis e gestão de múltiplas contas fazem parte do MVP. Consulte [a diretriz vigente](../docs/15-CONFIGURACAO-E-MULTIPLAS-CONTAS.md), que prevalece sobre referências anteriores a conta única. Implementação e contratos executáveis ainda pendentes.

Prefixo interno /api/v1. JSON UTF-8; IDs UUID internos e strings externas; timestamps RFC3339 UTC. Sessão em cookie HttpOnly e CSRF para escrita. Paginação por cursor opaco; limit padrão 25, máximo 100. Erro: {"error":{"code":"...","message":"...","request_id":"...","details":{}}}. Nunca retornar payload bruto Meta ou segredo.

## Rotas alvo

| Método/rota | Papel | Função |
|---|---|---|
| POST /api/v1/auth/login | Público com rate limit | Login administrativo |
| POST /api/v1/auth/logout | Autenticado | Revogar sessão |
| GET /api/v1/auth/me | Autenticado | Usuário, organização e papel |
| GET /api/v1/instagram/connect | Admin | URL OAuth com state |
| GET /api/v1/instagram/callback | Sessão/state válidos | Trocar code, redirecionar ao painel |
| GET /api/v1/instagram/connection | Admin | Saúde sem token |
| POST /api/v1/instagram/disconnect | Admin | Cancelar fila e eliminar credencial |
| GET/POST /api/v1/products | Leitura operator/admin; escrita idem | Listar/criar produto |
| GET/PATCH /api/v1/products/{id} | Operator/admin | Ler/editar; arquivar por status |
| POST /api/v1/media/sync | Operator/admin | Criar job de importação |
| GET /api/v1/media | Operator/admin | Mídias próprias paginadas |
| GET/POST /api/v1/campaigns | Operator/admin | Listar/criar rascunho |
| GET/PATCH /api/v1/campaigns/{id} | Operator/admin | Ler/criar nova versão |
| POST /api/v1/campaigns/{id}/simulate | Operator/admin | Regra pura, sem despacho |
| POST /api/v1/campaigns/{id}/activate | Operator/admin | Validar e ativar |
| POST /api/v1/campaigns/{id}/pause | Operator/admin | Reter jobs não despachados |
| POST /api/v1/campaigns/{id}/archive | Operator/admin | Cancelar pendências e arquivar |
| GET /api/v1/history | Todos | Eventos/resultados sanitizados |
| GET /api/v1/dashboard | Todos | Métricas operacionais |
| POST /api/v1/operations/pause | Admin/operator | Pausa global |
| POST /api/v1/operations/resume | Admin/operator | Retomar sem backlog automático |
| GET /api/v1/audit | Admin | Auditoria |
| POST /api/v1/privacy/deletions | Admin | Solicitação de exclusão |
| GET /health/live | Público sem detalhe | Processo vivo |
| GET /health/ready | Restrito à infraestrutura | Dependências prontas |
| GET/POST /webhooks/instagram | Protocolo Meta | Handshake e entrega assinada |

Não há endpoint de resend para unknown. Gestão de convites/membros terá rotas administrativas no provedor escolhido e contrato adicional antes de M1. CSV P1 não faz parte deste contrato MVP.

## Escritas e concorrência

POST de criação exige Idempotency-Key UUID; backend guarda organização/ator/rota/hash do body e resposta por 24h. Mesma chave e body → mesma resposta; chave com body distinto → 409. Mudança exige expected_version em body; divergência → 409. Ativação duplicada é idempotente se mesma versão; violação de campanha única → 409. Datas/links/regra inválida → 422; limite administrativo → 429. Essas chaves internas não equivalem a idempotência do endpoint Meta.

## Exemplo de produto

```json
{"name":"Luminária","description":"Modelo divulgado no Reel","links":[{"label":"Comprar","url":"https://shopee.com.br/EXEMPLO","position":1}]}
```

## Exemplo de rascunho

```json
{"name":"Luminária outubro","media_id":"UUID_INTERNO","product_id":"UUID_INTERNO","keywords":["LINK","QUERO"],"match_mode":"whole_word","template":"Olá! Aqui está {{product_name}}: {{product_links}}","starts_at":null,"ends_at":null}
```

## Evento normalizado interno

```json
{"schema_version":1,"account_id":"UUID_INTERNO","event_key":"CHAVE_ESTAVEL","type":"comment_created","comment_id":"ID_META","media_id":"ID_META","author_id":"ID_META_OU_NULL","text":"LINK!","occurred_at":"2026-10-16T03:00:00Z","received_at":"2026-10-16T03:00:01Z"}
```

Este objeto não é o payload prometido pela Meta: é o contrato do adaptador após validar/normalizar. Não confiar no formato do evento sintético para o contrato real.

## Meta

Contrato alvo: POST graph.instagram.com/{version}/{ig_user_id}/messages com Bearer e JSON recipient.comment_id/message.text. Resposta aceita deve ter identificação de mensagem validada pelo adaptador; campos diferentes do esperado não viram sucesso silencioso. Sanitizar erros e conservar trace_id quando existir. API version e limite de conteúdo são configuração obrigatória homologada.

## Sessão e suporte

GET auth/me retorna {user, csrf_token}; o frontend usa X-CSRF-Token em escrita autenticada. Login verifica origem, rate limit e proteção contra login CSRF; não depende de sessão preexistente. Idempotency-Key é obrigatório para POST administrativo (exceto login/logout e callback); guardar resposta sanitizada por 24h. Health ready usa credencial própria da infraestrutura, não sessão de operador. OAuth callback trata sucesso ou recusa, exige state e sessão correspondentes e não devolve token na URL.

## Contrato implementado no M0 com Supabase

A autenticação efetiva nesta fase é bearer do Supabase Auth, verificado por GET /auth/v1/user; as rotas de login/logout por cookie acima continuam alvo anterior ainda não implementado. O frontend autentica diretamente no Supabase Auth com publishable key e envia o access token no header Authorization. Não há signup administrativo público.

GET /api/v1/auth/me retorna `{user:{id,email},memberships:[{organization_id,role}]}`; sem membership, 403. GET /api/v1/instagram/accounts exige organization_id UUID e admin e retorna `{items:[...]}` sem tokens. GET /api/v1/instagram/connect exige organization_id e opcional account_id para reconexão; retorna `{authorization_url}` e define cookie Secure/HttpOnly/SameSite=Lax de 10 minutos. O callback aceita state/code ou recusa; usa vínculo de navegador com state persistido de uso único, verifica membership novamente e redireciona ao cockpit sem token/code na URL. As rotas singulares connection/disconnect e interface de edição continuam pendentes.

[OpenAPI M0](openapi-m0.json) descreve as rotas presentes; `openapi.yaml` permanece contrato alvo do restante do MVP.

### Página de autorização M0 e assinatura comments

GET /m0/connect serve página mínima de login Supabase e conexão OAuth, na mesma origem HTTPS da API. Somente URL e chave publishable/anon do Supabase são expostas no HTML; chaves secret/service-role são rejeitadas. Sessão do cockpit em memória; sem signup, armazenamento local ou painel completo. CSP com nonce restringe scripts e conexões, sem framing.

O callback agora retorna a /m0/connect?instagram=connected&comments=STATUS, sem token/code no destino. Salva e verifica descriptografia do token antes de solicitar POST /{ig_user_id}/subscribed_apps com subscribed_fields=comments, via graph.instagram.com/{version}. GET subsequente procura o campo comments para o app configurado. Status por conta: pending, accepted (Meta aceitou, leitura ainda não confirmou), confirmed (leitura confirmou app/campo), failed (não comprovado). Nenhum desses estados comprova recebimento de comentário real nem valida assinatura HMAC. A consulta de contas inclui comments_subscription_status e comments_subscribed_at. Nenhuma rota /messages é chamada por esse fluxo.

### Política pública

GET /privacy não exige sessão e retorna HTML da política MyAgentSales. Identidade do responsável e contato vêm somente de PRIVACY_CONTROLLER_NAME e PRIVACY_CONTACT_EMAIL ou PRIVACY_CONTACT_URL. Sem preenchimento, aviso provisório explícito; a rota não cria canal de atendimento, formulário, exclusão automatizada ou promessa de retenção.

### Diagnóstico protegido do webhook

GET /health/webhook exige X-Infra-Key e retorna contagens de requests POST por processo: received, persisted, invalid_signature, missing_secret, payload_too_large e storage_unavailable, além de início/última chegada e motivo. Sem payload, assinatura, token, IP ou IDs de conta. received conta qualquer origem e não prova Meta autenticada; persisted inclui duplicatas autenticadas aceitas, não necessariamente evento novo. GET de handshake não incrementa esses contadores. Reinício zera histórico; não substitui prova de comentário real nem permite atribuir tentativas passadas.

Em diagnóstico HMAC, `rejected_matches_instagram_oauth_secret` conta POSTs rejeitados pela chave configurada cuja assinatura coincide com a chave OAuth Instagram já existente. Comparação somente em memória e só visível por chave de infraestrutura; **não muda o 403, não grava payload e não autoriza por segredo alternativo**. Serve para localizar configuração incorreta, não para contornar assinatura.

### Resposta privada controlada M0 (CLI, sem rota pública)

Uma autorização fixa e consumida permite no máximo um claim persistente em m0_private_reply_attempts, com unicidade também por conta/comentário. sending é confirmado antes do POST /messages; HTTP200 exige message_id e confirmação do destinatário para accepted. Timeout, 5xx, resposta ambígua ou sending abandonado tornam-se unknown e não liberam reenvio; rejeição explícita vira failed, também sem retry neste teste. Segredos e texto do snapshot não ficam em resposta pública. A execução não altera DISPATCHES_PAUSED nem a pausa da conta. O registro fica em schema privado com RLS e sem privilégios anon/authenticated.

### Cockpit, pausa e PWA implementados

GET /api/v1/instagram/history exige bearer Supabase validado, organization_id e account_id UUID, admin e conta pertencente à organização. Retorna `{items:[{status,attempt_count,dispatched_at,finished_at,http_status}],dispatches_paused}`. Máximo50 registros recentes do teste controlado; sem dados de destinatário/token/mensagem.

POST /api/v1/instagram/accounts/{account_id}/pause exige os mesmos vínculos e organization_id. Operação idempotente de pausa retorna `{paused:true}`. Não há rota de retomada/envio. Essa chamada usa bearer explícito, não autenticação por cookie ambiente. Falha de autorização403; sessão ausente/inválida401. Escopo validado no banco.

GET /m0/connect serve cockpit; /manifest.webmanifest, /service-worker.js, /offline e /assets/icon-{192|512}.png são públicos. Cache do service worker limita-se a fallback e ícones; API e dados de sessão nunca são cacheados. Caminhos OAuth/webhook existentes permanecem iguais. OpenAPI executável em openapi-m0.json; descrição alvo OpenAPI YAML ainda não representa todo o runtime.

### Catálogo, campanhas e sessão persistente — implementação17/10/2026

O cockpit usa POST /api/v1/auth/login (email/password via HTTPS ao backend/Supabase), GET /auth/session e POST /auth/logout. Cookie __Host-cockpit opaco HttpOnly/Secure/Lax; tokens Supabase criptografados server-side, renovados com refresh token sob lock. Frontend não recebe access/refresh tokens. Origin exata no login; operações autenticadas por cookie exigem X-CSRF-Token e Origin. Backend continua validando identidade no Supabase e membership no banco. Bearer legado permanece suportado. Erros422 não ecoam entrada/senha.

Rotas /api/v1/catalog exigem admin e organization_id; as de publicações/campanhas/revisões também account_id. GET/POST products, PUT/DELETE products/{id} (DELETE inativa; expected_version); GET publications e POST publications/sync; GET/POST campaigns, PUT/DELETE campaigns/{id} (DELETE arquiva; expected_version); GET campaigns/{id}/versions; POST campaigns/{id}/prepare-pilot (expected_version,positive,negative); GET reviews e GET reviews/{id}. OpenAPI executável atualizado com modelos.

Campanhas salvam snapshots e versões imutáveis; exclusões de palavras prevalecem, mensagem deve conter product_links e passar limite UTF8 configurado. Revisão age-gated/sem envio consulta até75comentários, informa parcialidade, pré-elegibilidade e motivos; payload criptografado, prazo15min, histórico reabrível com flags expired/stale. Nenhuma reserva/tentativa de DM ou ativação é criada. Rascunhos/pausadas/arquivadas apenas; endpoint activate não existe.

Ver docs/18-COCKPIT-FUNCIONAL-E-PREPARACAO-PILOTO.md para semântica, segurança e impacto dos gates M0. Antes de liberar um piloto será necessário implementar os controles transacionais do despachante e revisar campanha/consentimento do operador.

## Acesso operacional —17/10/2026

Autorização por vínculo `memberships` na organização solicitada; metadados do Auth não definem papel. Admin/operator podem operar catálogo, publicações, campanhas, versões, simulação e histórico. OAuth e reconexão também aceitam operator na organização do vínculo; pausa de conta e arquivamento de campanha exigem admin. Conta/registro devem pertencer à organização do vínculo, inclusive para administrador em outra organização. Contas retornadas ao operador omitem escopos/IDs técnicos/orçamento. Nenhum token é retornado.

- `POST /api/v1/auth/invitation/session`: origem exata; recebe access_token/refresh_token do convite padrão Supabase, verifica ambos e vínculo antes de criar cookie BFF. JSON retorna usuário/CSRF, sem tokens; segredo somente no corpo, nunca query.
- `POST /api/v1/auth/password`: sessão cookie, origem e CSRF; password/confirmation mínimo12, atualiza exclusivamente usuário da sessão no Supabase. Sem senha padrão, persistência de senha local ou ID-alvo.
- `POST /api/v1/catalog/campaigns/{id}/simulate?organization_id=...&account_id=...`: admin/operator; expected_version, positive, negative; retorna correspondência/motivos, validade dos exemplos, mensagem/bytes, sending_enabled=false. Sem envio externo ou escrita de revisão.
- `POST /api/v1/catalog/campaigns/{id}/pause?organization_id=...&account_id=...`: admin/operator; expected_version; pausa com auditoria, rejeita versão obsoleta e campanha arquivada.

Provisionamento fora da API pública: `scripts/grant_operator.py` exige administrador do vínculo e usuário Auth existente, sem sobrescrever papéis. Procedimento em docs/19-ACESSO-OPERADOR.md. OpenAPI executável atualizado em openapi-m0.json.

## OAuth de Operador —17/10/2026, sessão23

GET /api/v1/instagram/connect exige admin/operator na organization_id solicitada, com account_id opcional pertencente à mesma organização. State persistido vincula ator, organização, intenção/conta e navegador; callback revalida membership no consumo e na gravação. Não usa organization_id fornecida no callback. Reconexão não troca identidade. Upsert recusa conflito com organização diferente também sob inserções simultâneas. Tokens permanecem criptografados e só no backend; retorno é redirecionamento sem credenciais. Contas novas/reconectadas ficam pausadas. Pausa de conta inteira/provisionamento continuam admin-only. Nenhuma alteração de schema/RLS.

## Seletor visual/paginação — sessão24

GET `/api/v1/catalog/publications` aceita `limit`1–25(padrão12), `cursor` opcional e retorna `{items,next_cursor,end_cursor,has_more_remote,synced_at}`; item inclui metadados de imagem/tipo e `automations` scoped. Cursor de cache criptografado, vinculado a organization_id/account_id/posição, TTL24h; cursor de outra conta é rejeitado. POST `/publications/sync` aceita `{load_more:false}` para atualizar recentes ou true para continuar o cursor do provedor salvo criptografado. Uma página25por chamada, host/caminho fixos; não segue nextURL externa. Estado de sincronização compara timestamp sob lock para detectar concorrência. Ambos admin/operator com vínculo e conta válida.

Criar campanha usa lock da publicação e409 se já há draft/paused nela; preserva históricos existentes e não permite reassociar publicação em edição. Arquivadas abrem versões na UI. Ativação continua ausente. Session resolve recupera401 de access_token por refresh uma vez, preserva rotação antes de falha de verificação temporária e não dispensa conferência de identidade. Sessão válida pode voltar por cookie sem novo login;503 temporário não equivale a401/revogação. Descrições antigas de sessão em memória são históricas.

## Configuração Shopee por organização —17/10/2026

As rotas abaixo exigem sessão Supabase válida, Origin/CSRF nos métodos de escrita e papel `admin` na `organization_id` informada. O backend verifica membership. `GET /api/v1/shopee/credentials?organization_id=...` retorna somente `{configured,configured_at,updated_at}`. `PUT /api/v1/shopee/credentials?organization_id=...` recebe `{app_id,app_secret}`; ambos são obrigatórios e substituem o par junto. Retorna somente `{configured:true}`. O App Secret nunca é devolvido, registrado ou inserido em mensagem de erro. As credenciais são cifradas com a chave existente antes da persistência em `instagram_link.shopee_organization_credentials`, isoladas por organização e inacessíveis às roles públicas do Supabase.

Essas rotas só guardam credenciais. Não executam chamadas à Shopee. Busca, ordenações, métricas, comissão, detalhes, geração de link e importação aguardam validação do schema no Explorer oficial autenticado. Não há endpoints de busca ou link descritos enquanto esses contratos forem desconhecidos.
