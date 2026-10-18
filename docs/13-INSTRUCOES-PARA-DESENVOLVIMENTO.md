# 13 — Instruções para implementação no Cursor

> Atualização de escopo (16/10/2026): configuração por variáveis e gestão de múltiplas contas fazem parte do MVP. Consulte [a diretriz vigente](../docs/15-CONFIGURACAO-E-MULTIPLAS-CONTAS.md), que prevalece sobre referências anteriores a conta única. Implementação e contratos executáveis ainda pendentes.

## Mandato

Implementar o MVP descrito neste pacote. Ler README, requisitos, regras, arquitetura, dados e contrato antes de escrever código. Este pacote substitui o protótipo colado no chat como referência de projeto. Não copiar endpoint/token incompatíveis do exemplo original.

## Ordem de execução

1. Criar repositório e estrutura da arquitetura; fixar versões suportadas e lockfiles.
2. Implementar apenas prova Meta: OAuth backend, webhook assinado, normalização e envio único controlado. Documentar evidência sanitizada. Se incompatível, registrar ADR e corrigir especificação antes de avançar.
3. Criar migrations com constraints, testes de unicidade e escopo.
4. Entregar autenticação administrativa e autorização no servidor.
5. Implementar domínio puro de campanha/gatilhos/versões/eligibilidade.
6. Implementar inbox durável, worker, locks, limitador, cooldown, lease e unknown.
7. Entregar painel funcional com simulação, ativação, pausa e histórico.
8. Implementar renovação, retenção, exclusão, observabilidade e backup.
9. Executar homologação e checklist; entregar instruções verificadas com comandos reais.

## Regras de engenharia

- Nenhum segredo real em fixture, seed, commit, screenshot ou comentário.
- Separar simulação de envio; testes por padrão usam adapter fake sem rede.
- Produção inicia com pausa global; ativação depende de configuração válida.
- Não adicionar chatbot, IA, scraping, automação de browser ou disparo em massa.
- Não chamar todo 5xx/timeout de retry seguro; seguir estado unknown.
- Não simular entrega/leitura quando só existe aceite.
- Não usar Redis sem necessidade medida; fila PostgreSQL é decisão inicial.
- Não desenvolver Facebook Login no MVP nem trocar host automaticamente.
- Contrato OpenAPI é alvo inicial; se mudar, atualizar spec, cliente e testes juntos.

## Entrega por item

Informar requisito atendido, mudança, como testar, evidências e limitação. Para mudança no estado de envio, incluir teste de concorrência/crash pertinente. Para mudança só visual, verificar fluxo e acessibilidade sem inventar testes que espelham o HTML.

## Prompt inicial reutilizável

“Leia esta documentação e implemente primeiro M0. Use somente Instagram Login. Não implemente o painel completo antes de provar OAuth, webhook real e um private reply via API oficial. Registre modalidade, versão e permissões homologadas sem expor segredos. Se faltar credencial, conclua a estrutura e testes simulados, informe o bloqueio e não declare integração validada. Depois prossiga em M1–M5, mantendo rastreabilidade dos RF e T.”

## Entrega final esperada

Repositório com código e infraestrutura; README com comandos reais testados; migrations; .env.example sem segredos; pipeline; testes e evidências; política preenchida pelo responsável; runbook e restauração ensaiada. Aprovação de código não equivale a aprovação da Meta.

## Continuidade obrigatória entre sessões

Instrução permanente do usuário: **sempre que concluir uma sessão, gere um arquivo de handoff para que qualquer agente ou modelo possa continuar o desenvolvimento**.

Antes de iniciar, leia `docs/HANDOFF.md` e o registro mais recente indicado nele. Antes de encerrar, inclusive em trabalho somente documental ou com bloqueios:

1. Crie `docs/handoffs/AAAA-MM-DD-NN.md`, com numeração incremental por data, preservando registros anteriores.
2. Registre objetivo, orientações do usuário, estado real da implementação, arquivos alterados, decisões, validações e seus limites, pendências, bloqueios, próximos passos ordenados e informações relevantes do ambiente/Git/processos.
3. Atualize `docs/HANDOFF.md` para apontar ao novo registro.
4. Informe o link do handoff na resposta final.

O registro precisa ser autossuficiente e distinguir implementação, teste simulado e homologação real. Nunca copie credenciais, tokens, senhas ou dados pessoais. As instruções também constam no `AGENTS.md` da raiz para descoberta automática por agentes.

## Evolução autorizada com envios pausados —17/10/2026

O usuário autorizou expressamente avançar cockpit funcional (produtos/links, campanhas por publicação, inclusão/exclusão, prévia e histórico) e sessão persistente Supabase enquanto pendências reais do M0 são investigadas. Esta orientação prevalece sobre uma leitura que paralise toda UI até cada verificação externa. Manter rastreabilidade do impacto: separar bloqueio técnico de ativação/envio de pendência de verificação que não impede cadastro e revisão. Consultar docs/18-COCKPIT-FUNCIONAL-E-PREPARACAO-PILOTO.md.

Preparar UMA campanha piloto com regras/mensagem/comentários pré-elegíveis antes de qualquer autorização de envio. Não inventar produto/links/post, não usar autorização única consumida do M0 como grant de campanha e não retirar pausa global para testar interface. Não declarar piloto ativo nem M0 integral homologado com base em testes simulados, sessão ou GET de verificação de webhook.
