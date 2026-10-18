# 15 — Configuração por variáveis e gestão de múltiplas contas

Diretriz do usuário em 16/10/2026. Este documento prevalece sobre premissas anteriores de uma única conta ou adiamento de múltiplas contas. Requisito definido; implementação ainda pendente. “Cota” foi interpretado como “conta” pelo contexto.

## Configuração

OAuth, integrações e configurações operacionais devem usar parâmetros, sem credenciais, URLs de ambiente ou identificadores de conta fixados no código. Variáveis de ambiente configuram a instalação; parâmetros persistidos configuram cada conta pela interface. Alterar uma conta não exige editar código, arquivo .env ou reiniciar a aplicação.

| Camada | Configuração | Gestão |
|---|---|---|
| Instalação | DATABASE_URL, SESSION_SECRET, TOKEN_ENCRYPTION_KEY, PUBLIC_APP_URL, API_PUBLIC_URL, INFRA_HEALTH_KEY | Ambiente/cofre do servidor |
| App Meta/OAuth | META_APP_ID, META_APP_SECRET, META_API_VERSION, META_OAUTH_REDIRECT_URI, META_WEBHOOK_VERIFY_TOKEN | Ambiente/cofre; validar no startup |
| Padrões operacionais | Janela, margem, orçamento, cooldown, timeouts, timezone e limites homologados da mensagem | Variáveis definem padrões; interface altera opções permitidas por conta |
| Conta Instagram | ID externo, nome de exibição, permissões, expiração, estado, preferências e pausa | Banco e interface administrativa |
| Credencial de conta | Token e metadados da autorização OAuth | Backend criptografado; nunca retornado à interface |
| Shopee Affiliate API por organização | App ID e App Secret da conta afiliada designada à organização | Cockpit, acesso somente Admin; cifrado com a chave existente antes de persistir; não usar variáveis globais ou credenciais de outra organização |

Limites de segurança e da plataforma são validados no backend. A interface não permite exceder limites homologados, substituir o host oficial por entrada arbitrária ou desativar assinatura do webhook. Opções modificáveis têm tipo, validação, padrão e auditoria. Valores aplicados devem ser consultáveis sem expor segredos.

Não usar um conjunto fixo de variáveis para cada conta (por exemplo, ACCOUNT_1_TOKEN). Um app OAuth configurado no ambiente poderá conectar várias contas, sujeito ao acesso efetivamente autorizado pela Meta. Variáveis de instalação não são editadas diretamente pelo navegador. A interface mostra configuração incompleta e orienta o administrador; não solicita App Secret ou chave de criptografia para cadastro de cada conta.

As credenciais do Shopee Affiliate Open API são diferentes das variáveis de instalação Meta: devem ser cadastradas pelo Administrador autenticado da organização em **Contas Instagram → Integração Shopee**. O App ID e App Secret são enviados por HTTPS ao backend e criptografados com `TOKEN_ENCRYPTION_KEY` antes de serem gravados no schema privado. O backend nunca retorna os valores nem os registra em logs. Operadores não podem consultar ou alterar essa configuração. Não preencher credenciais Shopee em `.env.local`, nem compartilhar credenciais entre organizações. A configuração apenas armazena os dados: nenhuma busca, geração de link ou chamada externa fica habilitada até o contrato oficial ser validado.

## Interface simples de contas

Disponibilizar página Contas com lista, busca, identificação da conta e saúde da conexão, e ações Conectar conta, Editar, Reconectar, Pausar/Retomar e Desconectar. O cadastro inicia OAuth; o backend valida identidade e permissões antes de persistir. Editar permite nome interno e preferências operacionais; trocar a identidade Instagram exige nova autorização, sem reassociar campanhas ou histórico existentes.

Administradores gerenciam configurações sensíveis e acessos. Por autorização do usuário em17/10/2026, Operadores também adicionam/reconectam contas profissionais por OAuth oficial na organização do vínculo, sem acesso às chaves técnicas; gerenciam campanhas e pausas de campanha permitidas. Consulta mantém acesso sanitizado. Toda autorização é validada no servidor com organização e conta.

Um seletor de conta filtra publicações, campanhas, fila, histórico e métricas. A conta selecionada deve estar visível durante operações. Cada campanha pertence a uma conta; mídia e credencial devem pertencer à mesma conta. Produtos podem ser compartilhados dentro da organização com snapshot na versão da campanha.

## Isolamento e processamento

O MVP passa a suportar várias contas na mesma organização. Isso não define cobrança ou SaaS multiempresa. Manter organization_id e testes de isolamento entre organizações.

Cada conta tem sua credencial, saúde, pausa, limite móvel e fila logicamente isolados. Uma falha ou revogação pausa a conta afetada. Pausa global continua bloqueando todas. O webhook roteia pelo identificador externo autenticado para a conta cadastrada; conta desconhecida não dispara envios. Chaves antirreenvio permanecem por conta/comentário. OAuth state deve vincular sessão, organização, intenção de conexão/reconexão e prazo de uso único; reconexão não pode substituir silenciosamente outra identidade.

## Critérios de aceite adicionais

- Configuração de ambiente incompleta impede iniciar os componentes dependentes com erro sem segredos.
- Conectar duas contas autorizadas, editar suas preferências e alternar a seleção sem editar código ou reiniciar.
- Reconectar uma conta preserva a outra e rejeita troca inesperada de identidade.
- Conta duplicada não cria segunda credencial ou vínculo conflitante.
- Campanha não usa mídia, token ou histórico de outra conta; IDs adulterados são negados.
- Pausa, revogação e orçamento de uma conta não interrompem outra; pausa global bloqueia ambas.
- Token, App Secret e OAuth code não aparecem em resposta, bundle, logs ou handoff.

## Ordem de implementação

Durante M0, preparar configuração tipada e fluxo OAuth para múltiplas contas. A prova real pode começar com uma conta; não comprova suporte real a duas. Antes de declarar gestão de múltiplas contas concluída, testar duas conexões e isolamento. Completar a interface após o gate técnico Meta, mantendo este requisito no MVP.

Atualizar OpenAPI, modelo executável e testes junto com a implementação das rotas de coleção de contas; as rotas singulares existentes são contrato anterior e ainda precisam de revisão. Não declarar suporte implementado apenas por atualizar a especificação.
