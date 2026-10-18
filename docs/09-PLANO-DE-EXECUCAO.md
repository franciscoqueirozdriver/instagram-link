# 09 — Planejamento e backlog

> Atualização de escopo (16/10/2026): configuração por variáveis e gestão de múltiplas contas fazem parte do MVP. Consulte [a diretriz vigente](../docs/15-CONFIGURACAO-E-MULTIPLAS-CONTAS.md), que prevalece sobre referências anteriores a conta única. Implementação e contratos executáveis ainda pendentes.

Estimativa inicial: 12–18 dias úteis de engenharia para uma pessoa experiente, com escopo deste MVP e acesso disponível. Não é compromisso; descoberta Meta pode alterar arquitetura e prazo. Esperas de aprovação, domínio, contratação e revisão jurídica não entram nessa faixa. Ajustar após M0.

| Marco | Esforço indicativo | Entregas | Dependência / saída |
|---|---|---|---|
| M0 Prova Meta | 1–3 dias | Login, webhook real, uma DM aceita, versão/scopes documentados | Conta elegível; gate de integração aprovado |
| M1 Fundação | 2 dias | Repo, CI, banco, auth/RBAC, ambientes e migrations | M0; testes de isolamento |
| M2 Catálogo/campanhas | 2–3 dias | Produtos, mídias, versões, editor e simulação | M1; ativação validada |
| M3 Processamento | 3–4 dias | Inbox persistente, worker, limite, estados, pausa e unknown | M1/M2; testes concorrentes |
| M4 Operação | 2–3 dias | Histórico, alertas, renovação, privacidade e backup | M3; restore aprovado |
| M5 Piloto e entrega | 2–3 dias | Homologação, manual, observação e correções | Todos P0 aprovados |

## Backlog executável

| Item | Entrega / tamanho relativo | Aceite principal |
|---|---|---|
| B01 | Adapter Meta e prova / M | Evento real e envio rastreado |
| B02 | Bootstrap e auth / M | Sem signup público; 401/403 |
| B03 | Schema/migrations / M | Constraints e restore inicial |
| B04 | Catálogo / P | Links validados e versionados |
| B05 | Importação de mídia / M | Paginação e propriedade |
| B06 | Campanhas / M | Uma ativa por mídia e simulação |
| B07 | Webhook inbox / M | Assinatura e commit antes do ACK |
| B08 | Regras do domínio / M | Casos de palavra, data, cooldown |
| B09 | Worker/limite / G | Concorrência e limite central |
| B10 | Timeout/crash/unknown / M | Sem repetição automática |
| B11 | Histórico/auditoria / M | Mensagem correta e segredo ausente |
| B12 | Saúde/renovação / M | Revogação pausa e alerta |
| B13 | Pausa/desconexão/exclusão / M | Jobs retidos/cancelados conforme regra |
| B14 | Deploy/backups/alertas / M | Restore e rollback ensaiados |
| B15 | Homologação / M | Evidências dos P0 arquivadas |
| B16 | CSV e reconciliação / M | P1 após piloto |

Tamanhos relativos P/M/G não equivalem a horas. M0 é caminho crítico; não desenvolver UI completa antes de verificar a integração.

## Definition of Ready

Item com requisito e aceite, dependências resolvidas, fixtures sanitizadas e decisão técnica necessária registrada. Não aceitar “fazer funcionar” como aceite.

## Definition of Done

Código revisado; testes pertinentes aprovados; migration validada quando houver; sem segredo no diff; observabilidade e tratamento de erro; docs atualizados; homologação em ambiente separado; evidências anexadas. Marco de produção exige checklist completo e plano de reversão.

## Evolução posterior

P1: reconciliação e CSV, métricas de fila, melhorias de UX. P2: múltiplas contas/empresas, fluxo de clientes e App Review, papéis por cliente, faturamento e suporte. Chatbot ou sequência de DM é outro escopo com nova análise de política.
