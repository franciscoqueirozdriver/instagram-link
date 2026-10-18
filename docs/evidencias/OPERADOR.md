# Evidências — acesso operacional na organização atual

Data:17/10/2026. Escopo restrito solicitado pelo usuário; leitura prévia de AGENTS, README, guia13, handoff20 e MD de evolução. Skills baseline-ui e accessibility-compliance-accessibility-audit aplicadas ao design existente. Não é implantação SaaS nem homologação integral do M0.

## Implementado

- `operator` reutilizado em memberships privadas, sempre por organization_id. Admin permanece restrito à organização correspondente. Metadata de Auth não promove papel.
- Operador: consulta de contas sem configurações técnicas/segredos, produtos/links (criar/editar/inativar), campanhas/regras/mensagens/versões, publicações, simulação pura, prévia, histórico e pausa de campanha.
- Admin: OAuth/reconexão/pausa de conta, arquivamento de campanha e provisionamento administrativo. Não há endpoint público para usuários autoatribuírem papel ou para ativar envios.
- Menu operacional Produtos, Campanhas, Publicações e Histórico, seleção de conta, conexão e pausa global. Design/tipografia/componentes existentes preservados; shell móvel permanece fixo com rolagem interna.
- Aceitação do convite padrão Supabase e senha própria via backend/cookie protegido, com origem/CSRF, tokens criptografados e identidade verificada no Supabase. Nenhuma senha padrão, senha armazenada pelo projeto ou sessão compartilhada.
- CLI `scripts/grant_operator.py`: usuário Auth existente, administrador na mesma organização, inserção idempotente de operador, sem substituir papel existente. Não é API de gestão global.

## Provisionamento real realizado

O usuário esclareceu que a conta já existia e forneceu o e-mail por canal de conversa. Consulta privada confirmou um único usuário Auth, e-mail confirmado e senha própria configurada. Foi criado/verificado o vínculo `operator` somente na organização atual, identificada pelo administrador existente e suas contas Instagram. Não foi criado outro usuário, enviado convite ou alterada senha. Dados pessoais não são reproduzidos nesta evidência.

Checagens após provisionamento: vínculos de administradores idênticos; novo usuário sem vínculo em outras organizações; hashes privados de credenciais, contas Instagram, produtos, campanhas, versões e tentativa M0 idênticos ao snapshot anterior. Pausa global e de todas as contas confirmada. Arquivo temporário contém somente hashes, não tokens/senhas. `.env.local` e chaves não alterados. Nenhuma migration ou política RLS alterada.

## Testes locais com simulações

- `.venv/bin/python -m pytest -q`: inicialmente63passed/1skipped sem PostgreSQL configurado.
- Regressão final com TEST_DATABASE_URL apontando exclusivamente para banco vazio `operator_cookie_final`, container `instagram-link-m0-lifecycle-test`,127.0.0.1:55443: **64passed em3,01s**. Migrations001–005 em banco de teste. Inclui operações SQL reais permitidas e negadas, conta/campanha de outra organização, admin em outra organização sem escalada, viewer negado, preservar administrador, cookie/login individual com Auth simulado, origem/CSRF/convite/senha, revogação de vínculo negando nova operação, regressões OAuth/HMAC/deduplicação.
- Primeiro teste PostgreSQL falhou porque a configuração fictícia não tinha meta_api_version e recebeu503 antes da autorização; corrigida para v26.0 e regressão repetida em banco vazio. Sem mudança do adaptador Meta.
- `node --check` em cockpit.js/catalog.js e compilação Python passaram.
- `NODE_PATH=/tmp/instagram-link-ui-tools/node_modules node scripts/ui/validate-catalog.cjs`: regressão administrativa passou, incluindo sessão restaurada após retorno OAuth simulado, catálogo/piloto/histórico, CSRF/logout/cache e Axe AA em seis larguras.
- `... node scripts/ui/validate-operator.cjs`: passou convite/senha fictícios, navegação operacional, ações administrativas403, produto/edição/inativação, publicações, campanha, simulação sem envio, pausa, histórico, sessão individual persistente e limpeza ao sair. Axe AA sem violações detectadas em320/390/768/1440px. Primeira asserção de menu incluía números decorativos; runner ajustado para os identificadores semânticos. Uma execução inicial aguardou publicações até timeout; diagnóstico isolado e repetição completa passaram, sem evidência de falha persistente. Fixtures não homologam Supabase Auth real.
- Capturas `docs/ui/operador-desktop.png` e `operador-mobile.png`, somente dados fictícios; inspecionadas visualmente. Teste não equivale a conformidade WCAG integral ou ensaio em celular físico.

## Verificações reais sem envio

`scripts/verify_supabase.py`:15tabelas com RLS; anon/authenticated sem USAGE/schema nem privilégios de tabela; roundtrip criptografado revertido; Auth rejeitou token inválido. Nenhum acesso público concedido.

API reiniciada na porta8000 com --no-access-log, túnel preservado. `UI_PUBLIC_URL=https://raises-formula-parameter-muslim.trycloudflare.com NODE_PATH=/tmp/instagram-link-ui-tools/node_modules node scripts/ui/check-public.cjs`: passou: cockpit/privacy200, sessão/catálogo sem login401, origem adversa403, Axe AA móvel sem violações. Não usa senha real, não abre OAuth e não envia DM.

## Pendências e relação com o plano

- Usuária deve entrar com seu e-mail/senha já existentes e confirmar uso real. Não foi solicitada nem usada senha real; não declarar login humano homologado.
- Convite por e-mail/definição de senha novos foram testados com fixture. Para futuros usuários, envio administrativo pelo Dashboard depende da URL de Auth correta; instalação tem chave pública sem secret administrativo. Não é bloqueio deste usuário existente com senha configurada.
- URL trycloudflare temporária; se mudar, revisar configuração aplicável antes de novos convites/OAuth.
- Mesma organização operacional entregue. EVO-04/EVO-13 não concluídos como SaaS; demais itens do MD e bloqueios do M0 permanecem no handoff20. Despachante não implementado/liberado. **Nenhuma nova DM, processamento geral pausado.**

## Manual de uso — sessão22,17/10/2026

Criado `docs/MANUAL-DO-OPERADOR.md`, restrito ao perfil Operador: acesso próprio, seleção de conta, produtos/links, publicações, campanhas, palavras-chave, mensagem/prévia, simulação, histórico e pausa. Distingue disponível/admin/não implementado, sem instruções de infraestrutura. Regras e nomes conferidos em pages/catalog.html, assets/cockpit.js/catalog.js e domínio campaigns.py. Não afirma simulação de comentários reais nem envio liberado.

Runner `scripts/ui/validate-operator.cjs` recebeu somente quatro capturas adicionais, sem mudança de fluxo ou código de produção. Nova execução passou integralmente com fixture isolada, incluindo convite/senha fictícios, menu, negativas administrativas, catálogo/campanhas/simulação/pausa/histórico, sessão/logout, Axe AA e quatro larguras. Quatro capturas novas e duas existentes referenciadas no manual; inspeção visual e checagem de existência dos seis arquivos realizadas. Sem dados reais, senhas visíveis ou credenciais. Compilação sintática JS e git diff --check passaram. Não repetida a suíte PostgreSQL da sessão21, pois alteração somente documental/capturas. Login humano da operadora continua sem confirmação; não confundir teste de fixture com isso. Nenhuma operação no Supabase ou Meta nesta sessão, nenhuma DM.

## Ampliação de OAuth e manual — sessão23,17/10/2026

Por nova autorização expressa do usuário, admin/operator agora podem conectar e reconectar contas profissionais pelo OAuth oficial dentro da organização do vínculo. As três etapas create_state/consume_state/save_connection revalidam membership; intenção de reconexão exige mesma conta. organization_id do callback não substitui contexto persistido. Upsert atômico impede conflito entre organizações sob concorrência; novas conexões/reconexões preservam paused=true. Viewer/revogação/acesso externo ao escopo continuam negados. Pausa de conta inteira, usuários/configuração e arquivamento de campanha continuam admin-only; nenhuma ativação de envios adicionada.

Navegação operacional passou a cinco destinos com Contas Instagram, lista por organização, nome/estado/validade/aviso de comentários, conectar/reconectar por cartão e estado vazio utilizável. Nenhum segredo/configuração técnica exposto. Espaço inferior ajustado à navegação fixa de cinco itens. Reutilizados componentes nativos/cores e skill baseline-ui; sem dependência nova.

Validação: **64passed em3,16s** com banco vazio operator_oauth_access no PostgreSQL descartável. Abrange OAuth de operador com SQL real e provider simulado, contextos/org/account, callback/replay, revogação entre etapas, token criptografado, preservação da outra conta/histórico, organização falsa no callback e corrida de inserções de uma conta em duas organizações: apenas uma vence e mantém sua credencial. Teste de API por sessão real local usa provider Auth simulado, sem senha real.

Browser final validate-operator.cjs passou inclusão e reconexão com navegação oficial interceptada localmente, callback real local e provider fake, sessão restaurada, três contas fictícias sem duplicação, estado vazio, bloqueios administrativos, catálogo/campanhas/simulação/pausa/histórico e Axe AA em320/390/768/1440. Primeira execução do runner encontrou título inicial ambíguo; ajustado seletor para heading nível1 e aguardo da lista de contas, repetição final passou. validate-catalog.cjs passou regressão administrativa e seis larguras. Capturas somente fictícias; duas novas de contas desktop/mobile e oito imagens do manual verificadas, com inspeção visual. Node--check, compileall e diff--check passaram.

Real: API reiniciada mantendo túnel. Check-public passou HTTPS cockpit/privacy200, privados401, login de origem adversa403, Axe móvel. verify_supabase passou15tabelas com RLS, sem grants de schema/tabela para anon/authenticated; probe revertido e Auth inválido rejeitado. Comparação privada de hashes antes/depois confirmou memberships, credenciais, contas, produtos, campanhas/versões, tentativa M0 e .env.local preservados. Nenhuma migration ou alteração de política RLS/chave. Pausa global e de todas as contas reais confirmadas.

Manual atualizado por nova permissão: inclusão, reconexão da mesma identidade, restrições de conta profissional/organização, aviso de assinatura, pausa de campanha e indisponibilidade de ativação/retomada; liberação geral fora da permissão do Operador. Não afirma login humano/OAuth externo novo homologado. Nenhum envio ou novo OAuth real nesta sessão.
