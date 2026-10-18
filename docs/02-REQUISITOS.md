# 02 — Requisitos e critérios de aceite

> Atualização de escopo (16/10/2026): configuração por variáveis e gestão de múltiplas contas fazem parte do MVP. Consulte [a diretriz vigente](../docs/15-CONFIGURACAO-E-MULTIPLAS-CONTAS.md), que prevalece sobre referências anteriores a conta única. Implementação e contratos executáveis ainda pendentes.

Prioridades: P0 bloqueia MVP; P1 melhora operação; P2 evolução.

| ID | Prioridade | Requisito | Critério de aceite |
|---|---|---|---|
| RF01 | P0 | Login administrativo e RBAC | Sessão ausente retorna 401; papel insuficiente 403; checagem no servidor |
| RF02 | P0 | Conectar conta por Instagram Login | Salvar conta e permissões efetivas sem expor token ao browser |
| RF03 | P0 | Saúde e renovação da conexão | Exibir válida/expirando/reconectar; revogação pausa envios da conta |
| RF04 | P0 | Catálogo de produtos e links | Bloquear URL insegura, produto sem nome e link vazio |
| RF05 | P0 | Importar mídias próprias | Paginação por cursor; não aceitar post arbitrário sem validar propriedade |
| RF06 | P0 | Campanhas versionadas | Criar, simular, ativar, pausar e arquivar; só uma ativa por mídia |
| RF07 | P0 | Detectar gatilhos | Correspondência normalizada, testável, por palavra ou frase |
| RF08 | P0 | Receber webhooks | Validar assinatura nos bytes originais; persistir antes de 200 |
| RF09 | P0 | Deduplicar eventos e envios | Repetições e workers concorrentes não criam segundo envio |
| RF10 | P0 | Enviar resposta privada | recipient.comment_id; salvar message_id quando disponível |
| RF11 | P0 | Limites e retentativas | Limite central por conta, backoff e classificação de falhas |
| RF12 | P0 | Histórico e auditoria | Filtro por campanha, período, status e motivo; sem segredos |
| RF13 | P0 | Pausa de emergência | Nenhum novo request começa após pausa confirmada; em voo pode concluir |
| RF14 | P0 | Tratar resultado incerto | Timeout após despacho vira unknown; sem reenvio automático |
| RF15 | P0 | Privacidade e desconexão | Cancelar fila e invalidar credencial; executar procedimento de exclusão |
| RF16 | P1 | Exportação CSV | Somente admin/operador, com auditoria e proteção contra fórmulas |
| RF17 | P1 | Reconciliação de comentários | Rotina paginada, limitada ao intervalo autorizado, mesma deduplicação |
| RF18 | P2 | Multiempresa | Isolamento, cobrança, consentimento e App Review específicos |

## Não funcionais

| ID | Objetivo proposto | Verificação |
|---|---|---|
| RNF01 | Segredos somente no backend, criptografia e HTTPS | Inspecionar bundle, logs e respostas |
| RNF02 | Webhook p95 < 2 segundos em carga alvo | 10 eventos/s por 5 minutos em homologação, incluindo lotes |
| RNF03 | Capacidade inicial 10 mil comentários/dia | Ensaio de persistência; envio continua sujeito ao teto externo |
| RNF04 | Aceite p95 ≤ 60s em condição normal | Medição por timestamps; excluir fila externa de forma explícita |
| RNF05 | RPO ≤ 24h e RTO ≤ 4h | Restaurar backup em ambiente isolado e cronometrar |
| RNF06 | Isolamento entre organizações no modelo | Teste de acesso com IDs de outra organização mesmo no MVP |
| RNF07 | Acessibilidade básica | Teclado, rótulos, contraste, estados sem depender só da cor |
| RNF08 | Observabilidade sem dados excessivos | Logs estruturados por IDs internos e códigos de erro |
| RNF09 | Versões reproduzíveis | Lockfiles, migrations e imagem identificada por commit |
| RNF10 | Sem promessa de exactly-once externo | Estado unknown e interrupção segura após falha |

Não há garantia de capturar todo comentário: webhooks e APIs externos podem atrasar ou falhar. Reconciliação reduz lacunas, sem alterar a janela de elegibilidade.
