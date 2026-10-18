# Instruções para agentes

Leia o README, `docs/13-INSTRUCOES-PARA-DESENVOLVIMENTO.md` e `docs/HANDOFF.md` antes de continuar o desenvolvimento. Consulte os documentos de domínio e contratos relevantes à tarefa.

## Handoff obrigatório ao encerrar cada sessão

Por instrução do usuário, ao concluir qualquer sessão de trabalho, crie um arquivo novo em `docs/handoffs/AAAA-MM-DD-NN.md` (numeração incremental por data, sem sobrescrever históricos) e atualize `docs/HANDOFF.md` com o link para o mais recente. Faça isso antes da resposta final, inclusive em sessões apenas documentais ou encerradas com pendências.

O handoff deve permitir continuidade por qualquer agente ou modelo sem depender do histórico da conversa. Inclua objetivo e orientações vigentes do usuário, estado implementado, arquivos alterados, decisões e motivos, testes/comandos com resultados e limitações, pendências e bloqueios, próximos passos em ordem, e estado relevante de ambiente/processos/Git. Diferencie testes locais de homologação externa. Não inclua segredos, tokens, senhas ou dados pessoais; referencie apenas os nomes das variáveis e arquivos de configuração.

Não declare etapas concluídas sem evidência. O M0 Meta precisa de homologação real antes de avançar para o painel completo, conforme a documentação.

## Configuração e múltiplas contas

Instrução do usuário: OAuth e restante da aplicação devem ser parametrizados; cadastrar, alterar e gerenciar várias contas por interface simples. Leia `docs/15-CONFIGURACAO-E-MULTIPLAS-CONTAS.md`. Variáveis de ambiente configuram instalação/app Meta; dados e tokens de cada conta ficam no banco, tokens criptografados. Não fixar uma única conta no código nem exigir editar .env para trocar/cadastrar contas. Esta diretriz substitui a restrição original de conta única no MVP.
