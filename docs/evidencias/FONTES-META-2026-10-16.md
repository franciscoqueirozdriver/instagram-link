# Consulta oficial direta — 16/10/2026

As consultas web renderizadas continuaram bloqueadas, mas GET direto via curl recuperou conteúdo oficial das páginas abaixo. Arquivos temporários locais em /tmp/instagram-link-meta-*. Não são fixtures de eventos reais e não contêm credenciais do projeto.

| Fonte oficial | Resultado útil |
|---|---|
| [Business Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/) | Define client_id como Instagram App ID e client_secret como Instagram App Secret, ambos da configuração de Instagram Business Login do produto Instagram. |
| [Setup Webhooks Subscriptions](https://developers.facebook.com/docs/instagram-platform/webhooks/) | Indica o App Secret de App settings > Basic; explica assinatura SHA256 do payload e comparação com X-Hub-Signature-256. Distingue verificação GET e payload POST. Documenta habilitação por subscribed_apps. |
| [Application](https://developers.facebook.com/docs/graph-api/reference/application/) | Define id do objeto Application como App ID. Não comprova sozinho que uma entrada específica de subscribed_apps pertence ao app geral esperado. |

Conclusão operacional: preservar o par OAuth Instagram e preencher META_WEBHOOK_APP_SECRET com o App Secret de Configurações do aplicativo > Básico, conforme a página de webhooks. Não usar verify token nem trocar o segredo OAuth. A validade real continuará condicionada à comparação HMAC de um evento recebido.

IDs: client_id do OAuth tem significado documentado de Instagram App ID. O id de um objeto Application é App ID; a identidade da entrada observada precisa ser comparada com o App ID público do painel. Não assumir igualdade com client_id nem remover vínculo ao app. A referência específica GET subscribed_apps tentada não estava disponível, portanto manter accepted e o verificador atual até essa associação ser comprovada.

Foi solicitado ao operador configurar o segredo somente no arquivo local e informar apenas o App ID público geral para comparação. Nenhum segredo foi solicitado no chat. Essas conclusões atualizam as pendências documentais das sessões anteriores; não equivalem a HMAC real homologado.

## Correção operacional por evidência criptográfica — 17/10/2026

A conclusão anterior sobre usar App settings > Basic foi supersedida para o emissor concreto desta integração. Um POST recebido no teste Instagram foi rejeitado pelo segredo geral configurado, mas sua assinatura coincidiu com o Instagram App Secret OAuth em comparação apenas diagnóstica (request permaneceu 403, sem persistência). Assim, orientar META_WEBHOOK_APP_SECRET com o segredo da seção Instagram Login nesse fluxo, preservando o segredo geral e demais chaves onde forem usados. A documentação genérica capturada não foi suficiente para determinar esse detalhe sem a prova real; não apresentar a indicação anterior como garantia para todas as modalidades.
