# 12 — Custos, riscos e decisões

## Modelo financeiro

Não há tarifa por mensagem/call anunciada para este fluxo Instagram equivalente à tarifação WhatsApp. Isso não é garantia comercial futura; verificar termos na implantação. Não foram cotados planos de fornecedores neste pacote.

| Componente | Custo a levantar |
|---|---|
| API Instagram | Sem cobrança direta por DM considerada no orçamento inicial; confirmar na implantação |
| API/worker | Processo contínuo, CPU/RAM e tráfego |
| PostgreSQL | Armazenamento, conexões e backup |
| Frontend/domínio | Hosting e renovação de domínio quando necessário |
| Observabilidade | Logs, alertas e retenção |
| Desenvolvimento | Horas × valor/hora + reserva de descoberta |
| Operação | Manutenção, mudanças Meta e suporte |

Fórmula: custo mensal = hosting + banco + backup + monitoramento + domínio/12 + manutenção. Custo inicial = implementação + configuração + homologação. Planos gratuitos podem suspender processos e não atender requisitos do worker; avaliar características antes de escolher. Não estimar preço de ManyChat ou VPS sem cotação atual.

Capacidade de envio é restrição externa, não recurso que se compra necessariamente com servidor maior. 600 tentativas/h é política local proposta; não é promessa de capacidade sustentada da Meta.

## Registro de riscos

| Risco | Probabilidade/impacto qualitativos | Resposta |
|---|---|---|
| Conta/permissão incompatível | Média/alto | M0 antes de UI |
| App Review demorado para clientes | Média/alto | MVP próprio; prazo externo separado |
| Mudança de API/política | Média/alto | Versão fixada, fontes e contrato |
| Pico de comentários excede limite | Média/médio | Fila e prazo; expirar sem resend |
| Duplicidade após crash | Média/alto | unknown, unicidade e teste concorrente |
| Links errados/desatualizados | Média/alto | Snapshot, simulação e pausa |
| Credencial comprometida | Baixa/alto | Cofre, criptografia e rotação |
| Eventos perdidos | Média/médio | Monitoramento; reconciliação P1 |
| Outra ferramenta consome limite | Média/médio | Inventário da conta e margem local |
| Dependência de pessoa única | Média/médio | Runbook, backup e acesso de recuperação |

## Decisões que o responsável deve confirmar

Nome e domínio; conta Instagram a usar; infraestrutura e orçamento; método de login administrativo; responsáveis e operadores; política de frequência 24h; texto e links de afiliados; retenção; contato de privacidade; necessidade futura de clientes externos. Defaults estão documentados para permitir desenvolvimento, mas campos reais não foram inventados.
