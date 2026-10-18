# Instagram Link — documentação do projeto

Versão 1.0 • 16/10/2026 • Idioma: português do Brasil

Aplicação para receber comentários em publicações de uma conta profissional do Instagram, identificar uma palavra-chave e enviar uma resposta privada com links de produtos, usando a API oficial da Meta.

**Estado: desenvolvimento iniciado no M0, sem homologação Meta.** As decisões deste pacote permitem começar o desenvolvimento; não significam aprovação da Meta nem implantação realizada. Nome provisório: Instagram Link.

## Como usar

1. Leia o PRD e as regras de negócio.
2. Execute primeiro a prova de integração descrita no guia Meta.
3. Registre os resultados no checklist de homologação. Só então implemente o restante.
4. Siga a arquitetura e os contratos; registre mudanças em ADR e atualize os testes.
5. Execute o plano de entrega por marcos e use o checklist de produção.

## Mapa da documentação

| Arquivo | Conteúdo |
|---|---|
| docs/01-PRD.md | Objetivo, escopo, personas, jornadas e métricas |
| docs/02-REQUISITOS.md | Requisitos funcionais, não funcionais e aceite |
| docs/03-REGRAS-DE-NEGOCIO.md | Elegibilidade, palavras-chave, versões, duplicidade e limites |
| docs/04-ARQUITETURA.md | Componentes, stack, fluxos e decisões |
| docs/05-MODELO-DE-DADOS.md | Entidades, índices, concorrência e retenção |
| docs/06-INTEGRACAO-META.md | Configuração oficial e prova de integração |
| docs/07-UX-E-TELAS.md | Telas, permissões, estados e mensagens |
| docs/08-SEGURANCA-E-PRIVACIDADE.md | Ameaças, controles e tratamento de dados |
| docs/09-PLANO-DE-EXECUCAO.md | Backlog, dependências, estimativas e entregas |
| docs/10-TESTES-E-HOMOLOGACAO.md | Casos, rastreabilidade e critérios de liberação |
| docs/11-DEPLOY-E-OPERACAO.md | Instalação futura, produção, backup e incidentes |
| docs/12-CUSTOS-E-RISCOS.md | Modelo de custo, riscos e decisões pendentes |
| docs/13-INSTRUCOES-PARA-DESENVOLVIMENTO.md | Ordem de implementação e orientação para Cursor |
| docs/14-FONTES-E-VALIDACAO.md | Fontes oficiais e pontos a confirmar |
| spec/API.md | Contratos HTTP internos e externos |
| spec/openapi.yaml | Contrato OpenAPI do backend da aplicação |
| templates/.env.example | Variáveis sem segredos |
| templates/CHECKLIST-PRODUCAO.md | Evidências exigidas para lançamento |
| templates/REGISTRO-DE-DECISOES.md | ADRs e questões abertas |
| templates/POLITICA-DE-PRIVACIDADE.md | Minuta com campos a preencher |

## Premissas adotadas

- MVP para uso próprio: uma organização, múltiplas contas Instagram, vários posts e produtos; preparado para expansão, sem SaaS comercial no primeiro lançamento.
- Instagram Login como única integração implementada inicialmente. Facebook Login é uma alternativa futura, não um fallback automático.
- Painel web; Python/FastAPI para API e worker; PostgreSQL para dados e fila persistente; React/TypeScript para interface.
- Sem IA, cobrança de clientes, publicação automática, prospecção ou sequência de mensagens.
- A integração Shopee Affiliate Open API está em preparação: o Administrador pode guardar App ID/App Secret criptografados por organização; a busca e a geração de links permanecem indisponíveis até validar o schema oficial da conta autorizada. Sem scraping.
- Todos os IDs da Meta são strings. Datas no banco em UTC; interface em America/Sao_Paulo.

Os documentos originais descrevem o alvo completo. A base implementada e os comandos disponíveis estão descritos abaixo; o MANIFEST.json identifica o pacote documental original, anterior ao desenvolvimento.

## Desenvolvimento — M0 com Supabase

API FastAPI e worker usam explicitamente `.env.local` na raiz. Persistência: PostgreSQL Supabase. Login do cockpit: Supabase Auth, com verificação do bearer token no backend e autorização por memberships privadas. Há base OAuth para várias contas, ainda sem homologação real Meta. Envios permanecem pausados.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
```

Para nova instalação, copie `.env.example` para `.env.local` e preencha a configuração. **Não sobrescreva o arquivo existente.** O utilitário `.venv/bin/python scripts/configure_local.py` preenche chaves ausentes/placeholder, preserva valores válidos e mantém a pausa; não rotaciona chave de criptografia já existente. Consulte [Supabase e homologação](docs/16-SUPABASE-E-HOMOLOGACAO-M0.md).

```bash
.venv/bin/python scripts/check_database.py
.venv/bin/python scripts/migrate.py
.venv/bin/python scripts/verify_supabase.py
.venv/bin/python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

O runner controla migrations por checksum no schema privado `instagram_link`; não reaplique SQL manualmente. Para verificar o worker M0 (checagem única, sem envios):

```bash
.venv/bin/python -m apps.worker.main
.venv/bin/python -m pytest -q
```

O teste de PostgreSQL exige `TEST_DATABASE_URL` apontando para banco descartável vazio; sem a variável, é skipped. Não use o Supabase real nesse teste de criação de schema. A verificação não destrutiva do Supabase usa `scripts/verify_supabase.py` e reverte a gravação sintética.

Crie/convide o usuário no painel Supabase Auth. Depois execute uma única vez `.venv/bin/python scripts/bootstrap_admin.py --user-id UUID_DO_USUARIO`. Não há cadastro administrativo público. Um usuário Auth sem membership recebe 403. O cockpit está disponível em `/m0/connect`, com sessão protegida por cookie seguro e renovação server-side no Supabase Auth. Consulte [o sistema visual e os testes](docs/17-SISTEMA-VISUAL-E-COCKPIT.md).

Neste ambiente Python 3.9 sem ensurepip, as dependências foram instaladas com `python3 -m pip install --target .venv/lib/python3.9/site-packages -r requirements.lock` após criar o diretório virtual sem pip. Para nova instalação, prefira Python 3.12 com venv disponível; essa versão ainda não foi testada nesta execução.

## Continuidade entre sessões

Antes de continuar o desenvolvimento, leia [o handoff mais recente](docs/HANDOFF.md). Por instrução permanente do usuário, toda sessão deve terminar com um novo arquivo de handoff e atualização desse índice, permitindo continuidade por qualquer agente ou modelo. O procedimento está no [guia de desenvolvimento](docs/13-INSTRUCOES-PARA-DESENVOLVIMENTO.md#continuidade-obrigatória-entre-sessões) e no [AGENTS.md](AGENTS.md).

## Configuração e contas — diretriz vigente

OAuth e configuração da instalação usam variáveis; contas e preferências são cadastradas e alteradas por uma interface simples, com suporte a várias contas no MVP. Consulte [configuração e múltiplas contas](docs/15-CONFIGURACAO-E-MULTIPLAS-CONTAS.md). O cockpit inicial permite conectar, selecionar, reconectar e pausar contas; edição de preferências e gestão completa permanecem pendentes.

## Autorizar conta no M0

Com API/túnel ativos e callback exato cadastrado na Meta, abra `/m0/connect` na origem HTTPS da API. Entre com seu usuário Supabase já vinculado como admin e clique em **Autorizar conta no Instagram**. O retorno valida permissões e persiste o token criptografado, mantendo envios pausados, depois solicita a assinatura de `comments`. A sessão é restaurada no retorno; confira o estado registrado. A assinatura de evento precisa também estar configurada no painel Meta; receber POSTs exige `META_WEBHOOK_APP_SECRET` correto. Esse é o cockpit inicial de conexões e resultados de homologação; campanhas e gestão completa permanecem pendentes.

## Política pública de privacidade

A rota `/privacy` é pública e servida pela mesma API, sem login. Ela descreve o estado implementado, incluindo teste privado manual controlado, retenção sem expurgo automático e procedimento manual de exclusão pelo contato configurado. Para finalizar, configure explicitamente `PRIVACY_CONTROLLER_NAME` e `PRIVACY_CONTACT_EMAIL` ou `PRIVACY_CONTACT_URL` no ambiente/`.env.local` e reinicie a API. Nenhum dado de login é usado automaticamente como identidade ou contato público.

Enquanto esses dados não forem fornecidos, a página mostra aviso provisório. Complete também a definição de base legal, retenção e condições de fornecedores com o responsável antes de tratá-la como política definitiva. A URL atual é `https://pumps-together-charts-stack.trycloudflare.com/privacy`; o túnel é temporário e a URL precisa ser substituída por domínio estável para operação definitiva.

Para diagnosticar ausência de eventos, `/health/webhook` exige `X-Infra-Key` e apresenta apenas contagens/horários de chegada, rejeição HMAC e persistência, desde o último startup. Consulte no backend sem expor a chave na conversa. Os contadores não guardam dados pessoais e não substituem a inbox persistente nem o teste de evento real. Não repetir comentários indefinidamente sem localizar a camada da falha.

## Teste privado único do M0

`scripts/m0_private_reply.py` é uma ferramenta administrativa isolada para a única autorização de homologação de 17/10/2026. Essa autorização já foi consumida; não é um worker, uma campanha ou endpoint público. O registro privado `instagram_link.m0_private_reply_attempts` mantém a reserva e no máximo uma tentativa. Não apagar ou reabrir esse registro, mesmo se o resultado for incerto. `--dedupe-check` verifica somente a barreira local sem invocar HTTP de envio.

O limite oficial validado para texto é 1000 bytes UTF-8 (`META_MAX_MESSAGE_LENGTH=1000`, `META_MESSAGE_LENGTH_UNIT=bytes`). A resposta privada usa recipient.comment_id; aceite da Meta não significa entrega ou leitura. O transporte não repete requests e resultados incertos preservam o bloqueio. A configuração geral e cada conta continuam pausadas. [Revisão e pendências do M0](docs/evidencias/M0-REVISAO-TESTE-PRIVADO.md).

## Saúde e ciclo de vida da credencial — M0

`.venv/bin/python scripts/check_token_lifecycle.py` consulta somente a identidade e a elegibilidade de renovação, mantendo token e pausas. Não envia mensagens nem renova/revoga credenciais. O adaptador `packages/meta/token_lifecycle.py` prepara renovação somente para token válido com pelo menos 24 horas e permissão básica; confirma identidade antes da troca criptografada com comparação da credencial anterior. Não há agendador nem endpoint de renovação instalado. Revogação/expiração detectadas podem marcar apenas a conta afetada como exigindo reconexão, sem apagar o token. Essa atualização também compara a credencial para rejeitar diagnóstico antigo.

Renovação, falhas e reconexão foram testadas com transporte simulado/PostgreSQL descartável; a execução externa desses três cenários continua pendente. Reconexão real requer interação do administrador em `/m0/connect`; o botão Reconectar vincula a intenção à identidade original por account_id. Não revogar a autorização real antes de coordenar a recuperação interativa. Não executar novamente a ferramenta de envio privado.

## Cockpit responsivo e base PWA

Acesse `/m0/connect` no HTTPS atual. Visão geral, contas/permissões e resultados usam conta selecionada; reconectar preserva a identidade e pausar não permite retomar envios. No celular, cabeçalho/contexto e navegação inferior ficam fixos; somente o conteúdo interno rola. Sistema visual, componentes, limites e reprodução dos testes em [docs/17-SISTEMA-VISUAL-E-COCKPIT.md](docs/17-SISTEMA-VISUAL-E-COCKPIT.md).

Manifesto, ícones e fallback offline preparam instalação PWA; dados privados não são cacheados. Lojas ficam para etapa posterior. O túnel temporário não é origem definitiva de distribuição.

## Produtos, campanhas e preparação do piloto

O cockpit agora cadastra/edita/inativa produtos e links ordenados, sincroniza publicações próprias, mantém campanhas e versões imutáveis por publicação e oferece inclusão/exclusão de palavras-chave, mensagem com prévia UTF-8 e histórico reabrível. A revisão do piloto analisa comentários com testes positivo/negativo e mantém a campanha pausada, sem criar tentativa de envio. A sessão Supabase sobrevive ao retorno OAuth por cookie seguro com tokens criptografados no servidor.

[Guia funcional, sessão e bloqueios reais do piloto](docs/18-COCKPIT-FUNCIONAL-E-PREPARACAO-PILOTO.md). É necessário entrar uma vez na nova versão para criar a sessão persistente. Nenhuma senha padrão é criada. Campanha ativa/dispatcher ainda não disponível e a pausa global é obrigatória.

Para manter a credencial Instagram: `scripts/check_token_lifecycle.py` é somente leitura por padrão; `--refresh` renova apenas se elegível (token válido com idade mínima24h), verifica identidade e grava com comparação da credencial anterior. Não envia mensagens nem revoga autorização.

## Acesso de Operador na organização atual

O cockpit aceita administrador e Operador com vínculo privado por organização. Operador trabalha em Produtos, Campanhas, Publicações, Histórico e Contas Instagram; pode conectar/reconectar contas profissionais por OAuth oficial na organização do vínculo, sem acesso a credenciais ou controles administrativos. Envios continuam pausados. Convite Supabase e definição de senha individual estão preparados; o provisionamento é administrativo, sem senha padrão. Consulte o [procedimento e matriz de permissões](docs/19-ACESSO-OPERADOR.md). Não configura SaaS nem acesso global.

Para quem opera produtos e campanhas: [Manual do Operador](docs/MANUAL-DO-OPERADOR.md), com exemplos e capturas de demonstração, sem instruções técnicas.

Para configurar credenciais Shopee localmente e consultar o estado da integração, veja [Integração Shopee](docs/21-INTEGRACAO-SHOPEE.md). Busca e geração de links permanecem bloqueadas até validação oficial do schema.

## Criação visual de automações

Nova automação começa por **Selecione uma publicação**, com grade de posts/Reels da conta escolhida, miniatura quando disponível, legenda/data e indicação de automação existente. Carregar mais percorre cache e novas páginas da API; atualizar lista não recarrega o cockpit. Selecionar abre configuração com resumo da postagem e prévia; rascunhos continuam pausados. A sessão renova no backend e falhas temporárias não devem pedir nova senha nem apagar campos. [Detalhes e limites](docs/20-SELETOR-VISUAL-DE-PUBLICACOES.md).
