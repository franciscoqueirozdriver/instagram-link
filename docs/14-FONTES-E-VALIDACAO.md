# 14 — Fontes oficiais e registro de validação

Consulta documental em 16/10/2026. Algumas páginas Meta impediram leitura integral automatizada com HTTP 429. Resultados indexados oficiais e coleção publicada pela Meta sustentam a orientação; configuração real, campos, limites de conteúdo e versão permanecem sujeitos ao gate M0. Não houve chamada autenticada à API ou acesso ao app do usuário.

| Fonte | URL | Uso |
|---|---|---|
| Meta — Instagram Platform overview | https://developers.facebook.com/documentation/instagram-platform/overview | Modalidades e níveis de acesso |
| Meta — Business Login for Instagram | https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/business-login | OAuth e contas próprias/terceiros |
| Meta — Send a Private Reply to a Commenter | https://developers.facebook.com/documentation/instagram-platform/private-replies | Uma resposta, janela de 7 dias, recipient.comment_id |
| Meta — Send Messages | https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/messaging-api | Mensageria e nível de acesso |
| Meta — Instagram webhooks setup | https://developers.facebook.com/documentation/instagram-platform/webhooks/setup | Assinatura do webhook e configuração |
| Meta — Webhooks getting started | https://developers.facebook.com/docs/graph-api/webhooks/getting-started/ | HMAC-SHA256 no corpo bruto |
| Meta — Messaging rate limits | https://developers.facebook.com/documentation/business-messaging/messenger-platform/overview/rate-limiting | 750 private replies/h para posts/Reels por conta |
| Meta — App Review Instagram | https://developers.facebook.com/documentation/instagram-platform/app-review | Acesso e revisão conforme modalidade |
| Meta — Instagram API collection | https://www.postman.com/meta/workspace/instagram/documentation/23987686-9386f468-7714-490f-9bfc-9442db5c8f00 | Instagram Login sem Página e scopes |

## Classificação da certeza

Documentado nas fontes consultadas: duas modalidades distintas; Instagram Login não exige Página; permissões da família instagram_business_*; envio por /messages com comentário como destinatário; private reply único com janela própria; assinatura SHA256; Standard/Advanced conforme contas atendidas.

Decisão do projeto: FastAPI/PostgreSQL/React; fila SQL; margem local 600/h; cooldown 24h; estados e política unknown; metas de desempenho; retenção e cronograma. Essas decisões não devem ser atribuídas à Meta.

Validar em M0: versão suportada exata; campos reais do webhook/comentário; scopes efetivamente necessários; assinatura da conta; permissões no app; expiração/renovação do token; tamanho máximo da mensagem e links; resposta de sucesso e erros; disponibilidade para contas/testadores elegíveis. Não inventar nomes atuais de botões nem garantir resultado de App Review.

Preço da API: o orçamento considera ausência de tarifa direta por esse fluxo, mas esta consulta não obteve tabela comercial oficial específica. Reconfirmar termos antes de contratar ou prometer preço a terceiros.

## Manutenção

Revisar mensalmente e antes de atualizar versão ou lançar para clientes. Registrar data, URL, diferença e impacto; atualizar regra, adaptador e testes no mesmo ciclo. Alterações de política de continuação de conversa não afetam MVP, que não faz follow-up.

## Shopee Affiliate Open API — verificação inicial 17/10/2026

Fontes oficiais: [Affiliate Open API Explorer](https://open-api.affiliate.shopee.com.br/explorer/v2), [Termos do Programa de Afiliados Brasil](https://help.shopee.com.br/portal/10/article/124094-Programa%20de%20Afiliados%20da%20Shopee%20-%20Termos%20e%20Condi%C3%A7%C3%B5es) e [Ajuda do Programa de Afiliados](https://help.shopee.com.br/portal/4/article/93461-Programa%20de%20Afiliados?seo=1).

Verificado: o Explorer oficial solicita App ID e Secret; sua interface indica consulta GraphQL. Os Termos oficiais definem links de afiliado como material do programa, determinam uso nas mídias aprovadas do afiliado e vedam scraping/extração automatizada de dados. Credenciais Shopee não estavam configuradas durante esta verificação e o schema não ficou acessível. Portanto, busca por palavras-chave, filtros/ordenações, dados de vendas/ranking e janela, comissões, preço/moeda, imagem/loja/disponibilidade, geração/atribuição de link, paginação, limites, assinatura, cache e licença de reuso permanecem não confirmados. Não inferir capacidades a partir de documentação de terceiros; não habilitar busca ou geração de links até conferir o schema e validar a atribuição com credenciais da organização. O estado atual do código e do cofre está em [docs/21-INTEGRACAO-SHOPEE.md](21-INTEGRACAO-SHOPEE.md).
