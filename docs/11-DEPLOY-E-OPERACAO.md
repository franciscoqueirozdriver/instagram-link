# 11 — Instalação, deploy e operação

Este runbook define o ambiente que o desenvolvimento deve entregar. Os arquivos de infraestrutura e comandos próprios ainda precisam ser implementados; não executar como se a aplicação já existisse.

## Desenvolvimento local, quando o repositório estiver pronto

1. Instalar Git, Docker/Compose, Python e Node nas versões fixadas pelo repositório.
2. Clonar o repositório e copiar templates/.env.example para .env fora do controle de versão; preencher segredos locais.
3. Subir PostgreSQL e serviços: `docker compose up -d --build` usando o Compose a criar em infra.
4. Aplicar migrations pelo comando documentado no README de implementação; impedir auto-migrate concorrente na inicialização de todos os workers.
5. Executar bootstrap administrativo único, sem senha padrão. Guardar credencial inicial com segurança e exigir troca.
6. Validar /health/live e /health/ready, login e seed de dados fictícios.
7. Usar endpoint HTTPS público de homologação para webhook real; localhost sozinho não recebe eventos Meta.
8. Executar testes e M0 antes de campanha.

## Produção

Serviços: proxy TLS, web, API, worker, scheduler e PostgreSQL privado. Uma instância de scheduler com lock distribuído no banco; vários workers só após teste de limite compartilhado. Configuração de produção separada de homologação, incluindo app/conta Meta de teste quando possível. Sem banco exposto à internet.

Pipeline: lint/tipos → testes → build imutável → scan de segredos → backup pré-migration → migration compatível → API/worker → readiness → smoke → liberação gradual. A ordem exata de migration e código deve seguir compatibilidade expand/contract. Não aplicar alteração destrutiva em deploy automático.

## Saúde e alertas propostos

| Sinal | Ação |
|---|---|
| Conexão inválida | Pausar conta e alertar imediatamente |
| Token a ≤7 dias / ≤2 dias | Aviso / alerta crítico; tentar renovação válida |
| Fila mais antiga >5 min | Investigar; distinguir limite esperado |
| unknown >0 | Abrir ocorrência e revisar sem resend automático |
| Falhas >5% em 15 min, mínimo 20 tentativas | Alerta e investigação; limiar ajustável no piloto |
| Banco/worker indisponível >2 min | Alerta de disponibilidade |
| Backup ausente há >26h | Alerta crítico |

Readiness da API exige banco; saúde do worker por heartbeat, não por endpoint web que ignore processo parado. Coletar queue_age, events_received, decisions por motivo, requests, accepts, unknowns e orçamento restante. Nunca usar IDs pessoais como labels de métricas de alta cardinalidade.

## Backup e restauração

Backup diário criptografado, retenção de 30 dias, destino externo ao host e acesso mínimo. Guardar chaves separadas. Teste mensal: restaurar em ambiente isolado, impedir envios externos, aplicar exclusões posteriores, validar integridade, registrar RPO/RTO. Após desastre, iniciar com pausa global até revisar sending/unknown e reservas de limite.

## Procedimentos

Token inválido: pausar → reconectar via OAuth → validar scopes → teste controlado → reavaliar jobs elegíveis explicitamente. Limite atingido: manter fila e respeitar cooldown, não criar novas contas/tokens para contornar restrição. Meta indisponível: pausar ou esperar; resultado ambíguo vira unknown.

DM incorreta: pausar campanha → verificar snapshot e configuração → corrigir com nova versão → documentar impacto. Não presumir capacidade de apagar mensagem já enviada.

Rollback: pausar dispatches → voltar imagem anterior compatível com schema → validar saúde → revisar jobs em voo → retomar. Não restaurar banco antigo por rotina, pois isso perde marcadores antirreenvio e pode duplicar mensagens.

## Rotina do operador

Diária: saúde, fila, falhas, unknown e campanhas. Semanal: links ativos, campanhas vencidas, capacidade e permissões. Mensal: restore, acessos, dependências e fontes Meta. Antes de atualizar API version: contrato em homologação e piloto controlado.
