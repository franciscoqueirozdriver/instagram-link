# Registro de decisões e questões abertas

Status iniciais: propostas para orientar implementação; confirmar após M0.

| ID | Decisão | Motivo | Revisão |
|---|---|---|---|
| ADR01 | Instagram Login | Conta própria sem dependência de Página | Se requisito de clientes mudar |
| ADR02 | Fila PostgreSQL | Durabilidade e menos componentes | Se throughput medir gargalo |
| ADR03 | unknown sem resend | Fronteira externa não atômica | Só com prova de idempotência externa |
| ADR04 | Snapshot de mensagem | Evitar troca de produto em job antigo | Sempre |
| ADR05 | Uma conta no MVP | Escopo e validação controlados | Após piloto |
| ADR06 | Limite local 600/h | Margem abaixo do teto documentado | M0 e operação |
| ADR07 | Cooldown 24h por campanha/autor | Reduz repetição | Confirmar com responsável |
| ADR08 | Credenciais Shopee Affiliate Open API cifradas por organização; sem busca/geração de link até confirmação do schema oficial | Evita compartilhar atribuição entre organizações e impede persistir/usar um contrato hipotético | Validar quando App ID/Secret aprovados estiverem configurados localmente |

## Modelo de ADR

ID/título: ___
Data/status: ___
Contexto: ___
Decisão: ___
Alternativas consideradas: ___
Consequências e limitações: ___
Requisitos/testes afetados: ___
Evidência e responsável: ___

## Questões abertas

Nome/domínio; conta alvo; infraestrutura; provedor de auth; usuários; retenção definitiva; responsável de privacidade; política de afiliado; necessidade multiempresa; disponibilidade de acesso Meta; versão e tamanho de mensagem suportados.
