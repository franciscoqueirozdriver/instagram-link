# Acesso operacional na organização atual

Implementação de 17/10/2026. Escopo autorizado: acesso próprio para um segundo usuário, como `operator`, na organização existente. Não cria empresa, cobrança, papel global ou administração de clientes. Relaciona-se à preparação de isolamento/onboarding do MD de evolução (EVO-04/EVO-13), sem concluir esses itens SaaS.

## Permissões reais

| Operação na organização do vínculo | Administrador | Operador |
|---|---|---|
| Consultar contas e resultados | Sim | Sim, sem configurações técnicas |
| Cadastrar/editar/inativar produtos e links | Sim | Sim |
| Criar/editar campanhas, regras e mensagens | Sim | Sim |
| Simular regras e visualizar mensagens/versões | Sim | Sim |
| Consultar publicações e histórico | Sim | Sim |
| Pausar campanha | Sim | Sim |
| Arquivar campanha | Sim | Não |
| Conectar/reconectar Instagram por OAuth oficial | Sim | Sim, na organização do vínculo |
| Pausar a conta inteira | Sim | Não |
| Provisionar vínculo de usuário | Comando administrativo local | Não |
| Credenciais e configurações da instalação | Ambiente administrativo | Não |
| Ativar envio | Não há endpoint implementado | Não |

A autorização é aplicada em cada método de persistência e deriva de `memberships(user_id, organization_id, role)`. Ser administrador de outra organização não confere administração nesta. O papel não vem de metadados editáveis do Auth nem de menus. `organization_id` e verificações de conta/registro foram preservados. Não houve migration, grants públicos ou mudança de RLS. Tokens não são retornados nem ao administrador.

O menu do Operador contém Produtos, Campanhas, Publicações, Histórico e Contas Instagram, com seleção de conta e conexão visíveis. Simulação operacional usa `/simulate`, sem chamada de mensagens ou consulta de comentários externos. Campanhas continuam rascunhos/pausadas. A prévia administrativa de piloto existente continua disponível sem liberar envios.

## Provisionar acesso sem senha padrão

1. Obter somente o e-mail da pessoa. Não solicitar senha ou compartilhar sessão administrativa.
2. No Supabase, Authentication → URL Configuration: conferir **Site URL** apontando para `https://raises-formula-parameter-muslim.trycloudflare.com/m0/connect`. Conferir também Redirect URLs. O convite padrão do Dashboard usa Site URL; apenas adicionar a URL na allowlist não muda o destino padrão. Esse túnel é temporário: revalidar domínio antes de convidar. Esta configuração não altera o callback OAuth do Instagram.
3. Authentication → Users → Add user → Send invitation. Usar o e-mail individual. Não criar senha. A conta Auth nasce no envio do convite; orientar a pessoa a aguardar o vínculo antes de abrir o link. Se já existe usuário, preservar sua identidade/senha e verificar acesso ou recuperação individual; não sobrescrever papéis existentes.
4. No ambiente administrativo, vincular **a mesma organização atual**, identificando seu administrador existente. Executar:

```bash
.venv/bin/python scripts/grant_operator.py \
  --email-file /caminho/privado/email.txt \
  --organization-id UUID_DA_ORGANIZACAO_ATUAL \
  --admin-user-id UUID_DO_ADMINISTRADOR_ATUAL
```

O arquivo deve ter modo 0600; não versionar nem copiar dados pessoais para evidências. O comando exige administrador nessa organização, usuário Auth existente e adiciona apenas `operator`. É idempotente para operador existente e recusa substituir admin/viewer. Não envia convite, não reseta senhas e não promove usuários globalmente. Nenhum endpoint público aceita autoatribuição de papel.

5. Após confirmar o vínculo, a pessoa abre o convite, define senha própria com pelo menos 12 caracteres e entra no cockpit. O fluxo padrão do Supabase entrega tokens no fragmento; o frontend retira o fragmento da URL, troca por sessão no backend e não grava tokens no localStorage. Backend verifica identidade no Supabase, vínculo e correspondência entre tokens, guardando acesso/refresh criptografados e cookie opaco HttpOnly/Secure. Definição de senha exige origem e CSRF, sem aceitar ID de terceiro. Não imprimir, copiar ou registrar o link de convite.
6. Validar login real, recarga e operações com a pessoa, sem enviar DMs. O teste automatizado usa apenas fixture e Auth simulado; não substitui entrega real de e-mail/convite.

O ambiente atual contém chave pública Supabase, sem chave administrativa de Auth. Portanto o agente não consegue enviar convite administrativo pela API com essa configuração. Usar o Dashboard autorizado acima; não fabricar JWT, inserir `auth.users` manualmente, pedir senha ou adicionar service-role ao cliente. O vínculo pode ser concluído depois que o usuário Auth existir.

Fontes oficiais: [convites e usuários](https://supabase.com/docs/guides/auth/users), [redirecionamentos](https://supabase.com/docs/guides/auth/redirect-urls), [templates de e-mail](https://supabase.com/docs/guides/auth/auth-email-templates). Convite padrão com fragmento suportado; templates personalizados com `token_hash` precisam de fluxo adicional e não devem ser ativados como se já estivessem implementados.

## Validação e limites

Testes SQL/HTTP cobrem operações permitidas, negação administrativa, viewer negado, conta/registro de outra organização negado, papel administrativo em outra organização sem escalada, papel de metadados ignorado e preservação do administrador. Testes de sessão cobrem convite, origem, CSRF, senha e identidade. Navegador isolado cobre menu, cadastro, prévia, histórico, responsividade e logout; evidências em `docs/evidencias/OPERADOR.md`.

Na entrega atual, o usuário informou que a conta já existia: foi localizada no Auth, com e-mail confirmado e senha própria configurada, e vinculada como operator somente à organização atual. Não houve convite, criação de usuário ou alteração de senha. Login humano com essa conta permanece pendente; ela usa o login normal com suas próprias credenciais. O procedimento de convite acima fica para futuros acessos que ainda não existam. Não há gestão gráfica de usuários nesta entrega. Não há liberação geral, despachante ou novo envio Meta. Pendências do M0 e do MD continuam vigentes.

## Ampliação autorizada — conexão pelo Operador, sessão23

Por orientação expressa do usuário, Operador também pode iniciar e concluir OAuth oficial para adicionar/reconectar contas profissionais dentro da organização do vínculo. Create_state, consume_state e save_connection verificam admin/operator por usuário e organização; callback usa contexto persistido e não aceita outra organização vinda da URL. Revalida papel após revogação. Reconexão exige a identidade original e preserva conta/histórico. Upsert atômico recusa conflito de conta de outra organização inclusive sob concorrência. Todas as conexões mantêm paused=true.

A nova seção Contas Instagram permite conectar e reconectar por cartão, com validade/estado e aviso de assinatura pendente, sem escopos técnicos, credenciais ou parâmetros da instalação. Opera também em organização sem conta. Pausa da conta inteira, usuários/configuração técnica e arquivamento de campanha continuam administrativos. Sem nova migration/grant/RLS, sem exceção por pessoa. Manual atualizado com capturas fictícias. Não equivale a homologação real de duas contas ou operação SaaS.
