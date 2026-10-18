# Seleção visual de publicações e continuidade da sessão

Implementado em17/10/2026, por solicitação do usuário. Complementa o cockpit existente sem ampliar SaaS, ativação ou envio.

## Antes e depois

Já existiam sincronização real pelo edge media da conta, armazenamento por organização/conta e editor com regras, produto e prévia. A consulta ficava limitada a3páginas25itens; metadados não guardavam miniaturas e a edição usava dropdown de legendas. Não havia continuação visível para posts antigos nem prevenção de dois novos rascunhos simultâneos na mesma publicação.

Agora Nova automação abre Selecione uma publicação, grade visual de posts/Reels existentes com data/legenda, miniatura quando disponível/fallback, seleção nativa por radio e automação existente. Após escolher, a grade se recolhe e o resumo da publicação fica junto da configuração. Trocar publicação preserva campos de um rascunho novo. Abrir automação existente edita conteúdo, sem trocar publicação; arquivada abre versões para consulta. As versões e históricos antigos permanecem intactos. Admin e operator têm o mesmo fluxo operacional, scoped pelo vínculo, sem exceções de usuário.

## Paginação e persistência

Migration006 aditiva: publications ganha thumbnail_url,media_url,media_product_type; instagram_accounts ganha publications_cursor bytea e publications_synced_at; índice ordenado organization_id/account_id/published_at/id. Nenhuma tabela ou dado anterior removido, nenhuma alteração de RLS/grants.

GET /api/v1/catalog/publications agora retorna items,next_cursor,end_cursor,has_more_remote,synced_at,limit1–25(padrão12). Cursor de cache Fernet vinculado a organização/conta/posição e validade24h. Ordem estável timestamp/id. Não aceita URL de paginação do usuário. Itens incluem resumo das automações existentes da mesma publicação/organização/conta.

POST publications/sync recebe load_more=false(padrão) para reiniciar a leitura recente ou true para continuar. Lê uma página25itens no host fixo graph.instagram.com com bearer no header; nunca segue paging.next arbitrário. Cursor bruto da Meta fica criptografado no servidor, não no navegador. Compara synced_at sob lock para não aplicar páginas concorrentes fora de ordem. Atualizar preserva publicações antigas já em cache; Carregar mais esgota cache e então avança o cursor do provedor. Ao trocar conta/sair, gerações invalidam respostas antigas e limpam seleção/editor. Nenhuma chamada a messages.

URLs de imagem aceitas somente HTTPS nos CDNs da Meta (cdninstagram.com/fbcdn.net), sem credenciais/query access_token. CSP de img permite só self e esses domínios. Imagem lazy, dimensões fixas/referrerPolicy no-referrer; falha vira fallback e não impede identificar pelo texto. Não há proxy arbitrário, cópia permanente nem cache offline de conteúdo privado. URLs assinadas de imagens podem expirar; atualização depende de acesso válido à Meta.

## Regras por publicação

Create/update validam usuário/organização/conta/produto/publicação. Conta precisa constar conectada para criação. Row lock na publicação serializa criação; já existir draft/paused causa409 em novo create. Não apaga duplicações históricas nem muda o plano de uma única campanha ativa por mídia. Campanha arquivada continua imutável; regra de ativação futura permanece bloqueada. UI oferece abrir a automação existente em vez de criar outra. Edição não reassocia silenciosamente a publicação.

## Sessão

Já havia cookie HttpOnly/Secure com persistência e refresh tokens criptografados; identificados caminhos que apresentavam login na restauração indisponível e não recuperavam access_token recusado antes do timestamp local. Agora a tela inicia restaurando acesso; erro temporário mostra tentativa novamente sem invalidar cookie. Retorno de visibilidade/BFCache verifica sessão em segundo plano e, para a mesma identidade, atualiza apenas CSRF/estado de acesso, preservando editor/campos. Não executa location.reload nem desconexão automática do Instagram. Sair continua explícito e eficaz.

No backend, se GETuser rejeita access_token com401 antes do timestamp previsto, tenta refresh uma vez sob lock. Rotação válida é persistida antes de uma segunda consulta de identidade para que falha temporária dessa consulta não reverta o novo refresh token. Identidade continua validada antes de autenticar; não aceita assinatura/token inválido nem ignora revogação. Prazo absoluto configurável permanece inalterado. Não persistir JWT/password no frontend para contornar a sessão.

## Verificações e limites externos

Evidências em docs/evidencias/SELETOR-PUBLICACOES.md. Consulta oficial real foi negada por permissão inclusive com os campos antigos; a conta já estava reconnect_required antes dessa leitura. Não alterada conexão, token ou status para contornar. Cinco publicações reais em cache foram percorridas por admin/operator; miniaturas novas e paginação externa real permanecem pendentes de autorização. Paginação externa e imagens foram verificadas com provider simulado. Não se trata de homologação Meta adicional ou piloto ativo. Nenhuma nova DM, nenhuma ativação.
