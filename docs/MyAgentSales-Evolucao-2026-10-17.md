# MyAgentSales — registro de evolução e pendências

Data: 17/10/2026. Base: relatório fornecido pelo responsável, referente a docs/handoffs/2026-10-17-20.md. Esse handoff e o código não foram disponibilizados para inspeção nesta revisão.

## Resultado da tentativa de inspeção

Foi aberto o endereço informado do cockpit em /m0/connect. O navegador retornou “Your request was blocked”. Não foi possível conferir login, telas autenticadas, dados ou fluxos. A causa do bloqueio não foi determinada. Não houve alteração na aplicação, autorização OAuth, ativação de campanha ou envio de DM.

Este registro consolida evolução e backlog; não é auditoria de código, certificação de conformidade ou atualização aplicada ao repositório.

## Estado informado pelo desenvolvimento

| Área | Estado relatado | Limite da evidência disponível aqui |
|---|---|---|
| Produtos | Links ordenados, edição e inativação | Relatório, sem inspeção direta |
| Campanhas | Por publicação, palavras-chave e prévia | Relatório, sem inspeção direta |
| Versões/histórico | Versões imutáveis e comentários pré-elegíveis | Pré-elegibilidade não significa autorização final de envio |
| Sessão | Supabase Auth persistente, cookie seguro e renovação servidor | Atributos e fluxos não auditados |
| Estados | Conexão, pausa e identificação da assinatura separados | Não conferidos visualmente |
| Mídias | 5 publicações reais sincronizadas | Relatório do desenvolvedor |
| Testes | 62 aprovados e fluxos fictícios em seis larguras | Sem execução ou acesso aos resultados brutos nesta revisão |
| Envios | Nenhuma nova DM; processamento pausado | Preservar até liberação específica |

O fluxo principal M0 já foi relatado como comprovado: OAuth, comentário real com HMAC, DM única recebida e deduplicação. Isso não substitui o teste no endereço HTTPS atual ou os controles completos do despachante.

## Direção de produto discutida

Preferência expressa: SaaS de autoatendimento, para reduzir trabalho manual de implantação/operação por cliente. Próximo passo de escopo: formalizar multiempresa e isolamento por cliente antes de abrir cadastro externo. Múltiplas contas na mesma organização, já previstas, não comprovam essa separação.

Experiência desejada: cliente cria login, entra no próprio espaço, conecta Instagram por OAuth, configura produtos/campanhas/gatilhos, testa, ativa e acompanha resultados. Sem copiar tokens ou configurar app Meta por cliente. Acesso externo depende das aprovações aplicáveis à integração.

## Prioridades e critérios de aceite

| ID | Prioridade | Trabalho | Evidência de conclusão |
|---|---|---|---|
| EVO01 | P0 piloto | Completar despachante com orçamento por conta, frequência, janela e antirreenvio | Testes de concorrência, reinício, expiração, limites e resultado incerto; sem segundo envio externo |
| EVO02 | P0 piloto | Comprovar comentário real assinado no endereço HTTPS atual | Evento identificado, HMAC válido e persistência confirmada |
| EVO03 | P0 piloto | Definir produto, links, post, gatilho e mensagem reais | Preview e versão revisados pelo responsável |
| EVO04 | P0 SaaS | Isolar organizações e autorização no backend/banco | Dois clientes sem acesso cruzado por API, UI, jobs ou OAuth; tentativas com IDs alheios negadas |
| EVO05 | P0 comercial | Cancelamento/opt-out e supressão | Solicitação bloqueia novos despachos e cancela fila aplicável; suporte também pode registrar solicitação externa |
| EVO06 | P0 comercial | Privacidade, exclusão, retenção e suporte | Fluxo executado, não apenas página; prazos e fornecedores refletem implementação |
| EVO07 | P0 comercial | Termos e autorização do cliente | Aceite versionado, autorização de contas e responsabilidades claramente registradas |
| EVO08 | P0 comercial | Verificar acesso Meta para contas de terceiros | Nível de acesso/aprovações documentados para o uso comercial efetivo |
| EVO09 | P1 | Esclarecer Application ID da assinatura comments | Significado dos IDs comprovado; verificador correto sem enfraquecer HMAC |
| EVO10 | P1 | Renovação real e revogação com recuperação | Evidências reais, preservação de conta e histórico; registrar mudança de elegibilidade se token trocar |
| EVO11 | P1 | Métricas operacionais por cliente/conta/campanha | Recebidos, elegíveis, fila, aceitos, falhas, incertos e expirados; sem inventar entrega/leitura/venda |
| EVO12 | P1 comercial | URL estável e operação de produção | OAuth, webhook, políticas, backups e alertas em infraestrutura estável |
| EVO13 | P1 | Onboarding autônomo | Cliente novo conclui login, OAuth e campanha sem intervenção técnica; reconexão compreensível |

P0 piloto refere-se à liberação controlada de campanha própria. P0 comercial refere-se à abertura do SaaS para clientes; não são gates equivalentes.

## Revisão das políticas: pendências registradas, não conclusões jurídicas

- Comparar exigências aplicáveis com código, testes e evidências em uma matriz auditável.
- Explicar no post que a palavra-chave solicita uma resposta privada; guardar contexto, versão e comentário que originou a resposta. Não interpretar como permissão irrestrita de marketing futuro.
- Implementar forma acessível de cancelamento, incluindo pedidos recebidos fora do Instagram, com bloqueio antes do despacho.
- Conferir suporte público e a obrigação de Página Facebook de suporte constante no texto fornecido. Distinguir essa obrigação da vinculação técnica de uma Página a cada conta Instagram.
- Revisar a aplicação das regras sobre anúncios de terceiros, promoções e links de afiliados ao conteúdo real enviado. Não presumir proibição geral ou autorização irrestrita apenas pelo HTTP 200.
- Mensagem e produto definidos pelo anunciante, sem conteúdo enganoso ou uso indevido de dados.
- Não aplicar automaticamente ao MVP seções de jogos, chamadas, Marketplace ou compra de anúncios; documentar aplicabilidade por recurso.
- Conforme surgirem fontes oficiais/decisões, registrar URL, data, conclusão, implementação e evidência. Quantidade de testes não equivale a conformidade integral.

## Limites e modelo comercial

A documentação inicial propôs orçamento local de 600 tentativas/h por conta; implementação atual precisa ser conferida, pois o despachante está pendente. Não tratar esse número como limite externo universal ou limite diário garantido. Uma franquia mensal por plano do SaaS será uma decisão comercial separada. Não prometer vendas, cliques ou recebimento com base somente no aceite da API.

## Ordem recomendada

1. Formalizar organização/cliente e auditar isolamento do que já existe.
2. Implementar supressão junto ao despachante e concluir testes de envio.
3. Definir campanha real e comprovar webhook no domínio atual.
4. Liberar somente piloto explicitamente delimitado, sem ativar backlog antigo automaticamente.
5. Concluir controles de privacidade, suporte, termos e acesso externo.
6. Evoluir onboarding, estatísticas e planos após validação dos gates comerciais.

## Orientação para o próximo handoff

Anexar este registro ao repositório; converter itens em backlog e relacionar requisito, código, teste, evidência, status e bloqueio. Preservar OAuth validado, tokens e chaves. Não ativar envios gerais nem afirmar revisão independente das telas com base neste documento.

## Registro de execução restrita — acesso operacional,17/10/2026

Por orientação posterior do usuário, implementado acesso `operator` na organização existente, reutilizando Auth/memberships/papéis, sem multiempresa, cobrança ou permissões globais. Backend preserva escopo de organização e controles administrativos; RLS não alterada. Navegação operacional e aceitação de convite com senha própria preparadas. Procedimento em [19-ACESSO-OPERADOR.md](19-ACESSO-OPERADOR.md), testes em [evidências](evidencias/OPERADOR.md).

Isso contribui para a separação de responsabilidades e futuro onboarding relacionados a EVO-04/EVO-13; não conclui isolamento SaaS entre clientes, onboarding comercial ou o restante do backlog. O segundo usuário já existia no Supabase Auth; vínculo operator criado na organização atual, sem alterar senha e sem novo convite. Login humano desse usuário ainda deve ser confirmado. Envios continuam pausados; esta entrega não resolve despachante nem declara piloto ativo ou M0 integralmente homologado.

### Ampliação operacional posterior — sessão23

O usuário autorizou Operador a também conectar e reconectar contas profissionais por OAuth oficial na organização do vínculo, sem acesso a chaves técnicas. Nova seção Contas Instagram, autorização nas três etapas e isolamento sob concorrência. Todas as conexões mantêm processamento pausado. Manual atualizado; não configura SaaS concluído, ativação de campanha ou homologação externa adicional.

### Correção operacional posterior — sessão24

Criação agora começa por grade visual de publicações existentes, com paginação por conta, abertura da automação já associada e configuração abaixo do resumo escolhido. Contribui para a preparação de campanha/onboarding (EVO03/EVO13), sem concluir SaaS/ativação. Sessão preservada ao retornar à tela, recuperação temporária sem recarga/desconexão e campos mantidos. Cache real de5publicações validado nos dois papéis; consulta externa atual depende de permissão da conta já marcada para reconexão. Não reconectar ou interromper trabalho em execução para testar. Manual atualizado; evidências específicas em SELETOR-PUBLICACOES.md.
