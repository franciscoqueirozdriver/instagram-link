# Revisão do teste privado único — 17/10/2026

Autorização do operador: uma única resposta privada ao comentário real previamente correlacionado. Nenhum processamento geral ou retry autorizado. Token/chaves preservados.

## Critérios antes da tentativa

| Critério | Evidência / estado |
|---|---|
| Instagram Login real | Conta e permissões obrigatórias comprovadas; token Fernet recuperável e não expirado |
| Webhook real | Corpo autenticado por HMAC e persistido; comentário correlacionado por ID na API |
| Endpoint private reply | POST graph.instagram.com/v26.0/{IG_USER_ID}/messages; recipient.comment_id |
| Janela | Comentário criado em 17/10/2026 04:41:45 UTC, inferior a sete dias; margem operacional de cinco minutos |
| Elegibilidade | Mídia na listagem própria, comentário visível e de nível superior, autor diferente da conta conectada e igual ao autor do webhook; lido novamente antes da tentativa |
| Limite | Fonte oficial de messaging indica texto UTF-8 de até 1000 bytes; configuração explícita 1000/bytes; mensagem de teste fixa com 70 bytes, sem link ou sequência |
| Single-use | authorization_key fixa exclusiva para todo o teste; UNIQUE conta/comentário e attempt_count limitado a 1 |
| Fronteira externa | sending/attempt_count=1 confirmados no banco antes do HTTP; retries=0, redirects desabilitados; timeout/5xx/missing ID levam a unknown, sem reenviar |
| Deduplicação | Concorrência de 40 reservas/claims e recuperação de crash comprovadas em PostgreSQL descartável; somente um claim; unknown nunca reabre |
| Escopo | Conta e DISPATCHES_PAUSED permanecem true; não há rota pública para disparar nem worker geral habilitado |

A normalização do offset +0000 real da Meta foi corrigida/testada em Python 3.9; não foi usado horário de recebimento como criação do comentário.

## Fontes oficiais consultadas diretamente

[Private Replies](https://developers.facebook.com/docs/instagram-platform/private-replies/) define recipient.comment_id, uma resposta e janela de sete dias, com message_id no sucesso. [Messaging API](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api/) define máximo de 1000 bytes UTF-8 para texto no endpoint messages. Texto oficial obtido por curl em /tmp/instagram-link-meta-private-replies.txt e /tmp/instagram-link-meta-messaging.txt.

## Pendências para declarar M0 concluído

- Retorno real registrado: HTTP 200, accepted, message_id e recipient_id guardados no registro privado; uma tentativa consumida. Isso não presume entrega.
- Recebimento visual confirmado expressamente pelo operador em 17/10/2026. Evidência humana de recebimento; não é callback de entrega/leitura da Meta.
- Deduplicação local no registro real validada: reserva e claim duplicados negados, attempt_count=1, sem invocar outro HTTP.
- Renovação/revogação detectada/expiração/reconexão simuladas agora comprovadas; execução real de renovação e ciclo revogação/reconexão ainda pendentes. Não há job de refresh implementado.
- Associação do Application ID retornado por subscribed_apps ao app geral permanece sem confirmação de identificador; inscrição aparece accepted embora comments e webhook real já estejam comprovados.
- Captura/normalização de eventos em fila e worker geral, retenção/expurgo, desligamento/exclusão operacional, backup/restore e demais critérios T01–T30 ainda pendentes para MVP/produção, não confundir com prova única de API.
- Túnel temporário, sem hospedagem/domínio definitivo. Políticas operacionais definitivas ainda dependem do responsável.

Nenhuma dessas pendências é escondida pelo envio de teste autorizado. Não declarar produção pronta ou homologação integral somente com message_id.

## Resultado observado

Única tentativa despachada em 2026-10-17T04:50:37.700949+00:00. HTTP 200; resposta com message_id e destinatário esperado, salva na tabela privada m0_private_reply_attempts. Não copiar IDs de mensagem/destinatário para documentos públicos. Confirmação visual de recebimento fornecida expressamente pelo operador em 17/10/2026; não houve novo envio.

PostgreSQL descartável: 29 testes completos aprovados antes da preparação; teste adicional do offset Meta +0000 aprovado na sequência. Regressão final: 29 unitários aprovados e um teste de banco opcional skipped. Deduplicação pós-envio no Supabase bloqueou reserva/claim sem chamar o transporte; uma tentativa persistida.
