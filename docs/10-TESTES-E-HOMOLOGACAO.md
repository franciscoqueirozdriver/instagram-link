# 10 — Testes e homologação

## Estratégia

Regras puras com unitários; PostgreSQL real isolado para locks/índices; transporte Meta simulado para erros e timeout; prova real de contrato para autenticação, webhook e envio. Mock não comprova permissão real. Não disparar carga de teste contra contas reais.

| Caso | Requisito | Cenário e resultado esperado |
|---|---|---|
| T01 | RF01 | Sem sessão 401; viewer alterando campanha 403 |
| T02 | RF02/03 | OAuth state inválido/reutilizado negado; token nunca aparece em resposta |
| T03 | RF04 | URL insegura rejeitada; vários links mantêm ordem |
| T04 | RF05 | 3 páginas de mídia importadas sem perder cursor; mídia alheia negada |
| T05 | RF06 | Duas ativações concorrentes: apenas uma campanha ativa |
| T06 | RF07 | LINK/link!/Quero LINK aceitos; linkado, vazio e gatilho ausente ignorados |
| T07 | RF08 | Corpo alterado/assinatura ausente negados; lote válido persistido |
| T08 | RF08 | Banco indisponível → 503; reentrega após recuperação processa uma vez |
| T09 | RF09 | 100 cópias do mesmo evento em lotes diferentes → um dispatch |
| T10 | RF09 | Dois workers no mesmo comentário → uma reserva e no máximo um despacho |
| T11 | RF10 | Conta/post/gatilho corretos → mensagem do snapshot correto e message_id |
| T12 | RF10 | Comentário próprio/aninhado/removido/sem timestamp confirmado → sem envio |
| T13 | RF11 | Janela móvel com limite local: tentativa excedente espera |
| T14 | RF11 | Erro de token pausa conta; erro permanente não gera loop |
| T15 | RF11 | Retry explícito seguro respeita atraso e expiração |
| T16 | RF14 | Timeout após possível despacho → unknown e nenhum resend |
| T17 | RF14 | Crash em sending, incluindo após aceite antes de commit → unknown |
| T18 | RF13 | Pausa confirmada bloqueia novo despacho; em voo é registrado |
| T19 | RF06 | Nova versão cancela/reavalia backlog conforme política, sem trocar produto silenciosamente |
| T20 | RF09 | Reinício do serviço preserva antirreenvio e cooldown |
| T21 | RF15 | Desconectar cancela fila, elimina token e impede novos sends |
| T22 | RNF06 | IDs de outra organização negados em todos endpoints |
| T23 | RNF01 | Bundle, logs e exportações sem token, segredo ou OAuth code |
| T24 | RNF05 | Restaurar backup e reaplicar exclusões; medir RPO/RTO |
| T25 | RNF02/03 | 10 eventos/s por 5 min, ACK p95 <2s e sem perda local |
| T26 | RF11 | Job fica velho na fila: expira antes de request externo |
| T27 | RF09 | Mesmo autor/campanha em 24h bloqueado; outro produto/post permitido |
| T28 | RF12 | Aceite exibido como aceite, nunca entregue/lido |
| T29 | RF15 | Pedido de exclusão alcança texto/payload e agenda limpeza de backup |
| T30 | RF03 | Refresh com condição inválida leva a reconexão sem expor token |

## Gate real Meta

Anotar modalidade, versão, scopes, acesso, conta de teste e horário. Receber comentário real → verificar assinatura → realizar uma resposta autorizada → confirmar visualmente DM → registrar retorno sanitizado. Não testar “segunda DM” como carga normal; deduplicação deve impedir request. Testar mensagens fora da janela por fixtures, evitando tentativas desnecessárias reais.

## Liberação

Todos P0 aprovados; T01–T30 sem defeito crítico aberto; versão Meta e limites confirmados; backup restaurado; alertas testados; política e contato preenchidos; campanha piloto revisada pelo responsável. Registrar data, commit, executor, resultado, evidências e limitações conhecidas. Se M0 falhar, não declarar sistema pronto.
