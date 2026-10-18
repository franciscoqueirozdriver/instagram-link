# Supabase e continuação do M0

Decisões confirmadas em 16/10/2026: Supabase Auth para o cockpit, PostgreSQL Supabase para persistência, FastAPI e worker Python, Instagram Login e várias contas por organização.

## Configuração local

API e worker usam explicitamente `.env.local` na raiz, via caminho absoluto. Variáveis do processo têm precedência; não há busca implícita de outros .env. `.env.local` é ignorado pelo Git e tem permissões 0600. A chave Fernet e o verify token foram gerados diretamente no arquivo sem exibir valores; chaves válidas existentes não são rotacionadas pelo utilitário.

`DATABASE_URL` teve somente o escape URI da senha corrigido. As credenciais preenchidas foram preservadas. `INFRA_HEALTH_KEY` também foi gerada. `DISPATCHES_PAUSED=true` é obrigatório nesta etapa; API e worker recusam configuração que habilite despachos. Não existe dispatcher de mensagens implementado.

`META_APP_ID` e `META_APP_SECRET` devem conter os identificadores do produto **Instagram > API setup with Instagram login**, não o ID/secret genéricos de Facebook Login. Há aliases opcionais `META_INSTAGRAM_APP_ID` e `META_INSTAGRAM_APP_SECRET`, com precedência. `META_WEBHOOK_APP_SECRET` é o segredo explícito do app que assina o webhook; não é inferido do segredo OAuth. Preencher conforme a configuração real de assinatura no painel. Confirmar a assinatura com o webhook real antes de homologar. Não usar verify token como App Secret.

Faltam Instagram App ID, Instagram App Secret, segredo explícito de assinatura do webhook e versão Meta suportada confirmada. O callback está configurado localmente e precisa ser substituído pelo HTTPS real. Os limites/unidade de mensagem continuam pendentes do gate real, antes de implementar envio.

## Banco

Antes das migrations, a conexão foi testada e o banco estava sem tabelas em public. Migrations 001 e 002 aplicadas pelo runner com transação, lock e checksums. A inbox inicial é movida para o schema privado `instagram_link`. Esse schema contém organizations, memberships, instagram_accounts, credentials, oauth_states, webhook_envelopes e schema_migrations.

Todas as tabelas têm RLS ativado e sem políticas públicas. Os papéis anon/authenticated não têm USAGE no schema nem acesso às tabelas. Credenciais e processamento só passam pelo backend com DATABASE_URL; não publicar esse schema na Data API. Não se alteraram tabelas de outros projetos nem configurações globais do Supabase Auth.

Cada conta tem token criptografado, expiração, scopes, pausa, orçamento e cooldown próprios. Não há fila/limitação executável ainda; os campos preparam esse processamento. A organização e cada conexão começam pausadas. Criar uma segunda conta não exige novas variáveis de ambiente.

## Auth e OAuth

O backend valida bearer tokens no serviço Supabase Auth por GET /auth/v1/user; só depois consulta memberships no banco. Não usa decode sem verificação ou metadata editável para autorização. Não há signup administrativo público. O bootstrap permite vincular uma única vez um usuário já criado/convidado no Auth; nunca recebe senha.

Rotas atuais: GET /api/v1/auth/me, GET /api/v1/instagram/accounts?organization_id=UUID, GET /api/v1/instagram/connect?organization_id=UUID[&account_id=UUID] e GET /api/v1/instagram/callback. Connect exige administrador, guarda hash de state e cookie de navegador (TTL 10 min), e retorna a authorization_url. O callback consome o state uma única vez, revalida vínculo, troca code por token no backend, valida identidade/permissões e grava credencial Fernet. Reconexão rejeita troca de identidade. Conflitos de conta não reassociam outra organização.

Fluxo preparado: autorização em www.instagram.com/oauth/authorize, code exchange em api.instagram.com/oauth/access_token e extensão em graph.instagram.com/access_token. Não há fallback para graph.facebook.com ou Page token. Respostas inesperadas ou permissões ausentes falham fechadas; o contrato exato de permissões/identidade ainda precisa do teste real. O arquivo apps/web/auth.ts prepara login/refresh/logout e consumo do backend; não há cockpit visual/build pronto nem login real validado.

## HTTPS para homologação

URLs locais exatas:

- Callback: http://localhost:8000/api/v1/instagram/callback
- Webhook: http://localhost:8000/webhooks/instagram

Inicie a API com `.venv/bin/python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --no-access-log`. `cloudflared` está disponível no ambiente. Um túnel temporário pode ser iniciado manualmente com `cloudflared tunnel --url http://127.0.0.1:8000`; ele fornece um domínio HTTPS. Nenhum túnel foi aberto nesta sessão.

Use o domínio retornado como API_PUBLIC_URL e substitua META_OAUTH_REDIRECT_URI por esse domínio mais `/api/v1/instagram/callback`. Cadastre essa URI exata no Instagram Business Login e o domínio mais `/webhooks/instagram` como callback de webhook, usando o verify token guardado no arquivo. Configure PUBLIC_APP_URL para a origem real do cockpit e reinicie API/worker. Um quick tunnel muda de endereço ao reiniciar; para testes repetidos, prefira túnel nomeado/domínio estável. Se cockpit e API ficarem em sites diferentes, publique-os na mesma origem com proxy para preservar o cookie OAuth.

Desabilitar query/access logs no proxy, no túnel e no servidor; httpx/httpcore são limitados a WARNING pela API para evitar registro de URLs com tokens de troca. Não ativar debug HTTP com credenciais reais.

## Fontes e limites

[Supabase JWTs](https://supabase.com/docs/guides/auth/jwts) e [getUser](https://supabase.com/docs/reference/javascript/auth-getuser) orientam a validação no serviço Auth. [Coleção oficial Meta — Instagram Login](https://www.postman.com/meta/instagram/folder/1z5vxzu/instagram-api-with-instagram-login) distingue a modalidade e scopes. A página [Business Login for Instagram](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/) não entregou conteúdo integral nesta consulta automatizada. Confirmar no painel autorizado os campos exatos e o segredo usado na assinatura. Nenhuma consulta autenticada ou DM Meta foi feita: M0 não homologado.

## Atualização de 16/10/2026 — túnel ativo

Foi aberto o quick tunnel https://modes-name-flag-listing.trycloudflare.com e .env.local atualizado com API_PUBLIC_URL e callback OAuth desse domínio. Os endereços localhost acima são referência de instalação, não os endereços atuais para cadastro. Use:

- Callback: https://modes-name-flag-listing.trycloudflare.com/api/v1/instagram/callback
- Webhook: https://modes-name-flag-listing.trycloudflare.com/webhooks/instagram

A API foi reiniciada. O túnel é temporário e muda se for recriado. META_API_VERSION=v26.0 validada em contrato simulado, sem prova autenticada. Credenciais gerais e Instagram Login ainda precisam de confirmação de origem pelo operador. O segredo exato de assinatura e limite/unidade de mensagem não foram confirmados na documentação oficial acessível nesta sessão; campos permanecem pendentes e envios pausados. Nenhum usuário Auth existe ainda; o bootstrap depende de criação/convite no painel e UUID do usuário.
