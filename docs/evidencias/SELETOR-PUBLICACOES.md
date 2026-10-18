# Seleção visual e sessão — evidências da sessão24

Data17/10/2026. Lidos previamente MD evolução (direção/backlog, não auditoria), handoff23, README/AGENTS/guias e contratos. Escopo restrito: publicação existente como primeira etapa, paginação, automação existente, Admin/Operador e continuidade de sessão. SaaS/RLS/organization_id preservados; nenhuma ativação ou mensagem.

## Implementado e lacuna corrigida

Antes havia media sync real limitada a75itens e editor com dropdown de legendas, sem miniaturas/paginação visível. Agora grade Selecione uma publicação inicia criação, com posts/Reels, imagem quando disponível/fallback, legenda/data, seleção e automação existente. Escolha recolhe grade, mantém resumo da postagem e abre configuração/prévia; Trocar publicação preserva campos novos. Existing automation busca conteúdo atualizado antes de abrir; arquivada abre versões. Criar/editar valida escopo e não troca publicação de campanha existente; lock na publicação impede dois drafts concorrentes. Não migra/apaga históricos antigos. Ativação permanece ausente.

Migration006 foi aplicada pelo runner após verificar5migrations rastreadas e5publicações reais: apenas novas colunas de metadados/cursor criptografado e índice de paginação.001–005 reconhecidas, checksums preservados.15tabelas privadas continuam RLS, sem grants anon/authenticated; verify_supabase passou com probe revertido e token inválido rejeitado. Sem alteração de usuário/roles/OAuth/configuração.

GETcache usa keyset timestamp/id com cursor Fernet vinculado a organização/conta, TTL24h,12itens padrão. Sync faz uma página25da Meta por chamada, after persistido criptografado no servidor; ignora nextURL arbitrária. load_more continua até fim, atualizar reinicia leitura recente sem remover cache antigo. Estado concorrente detectado por synced_at sob lock; troca de conta ignora respostas atrasadas. URLs de imagem restritas a CDNs Meta HTTPS, sem credenciais/access_token; CSP e fallback apropriados, sem cache offline privado.

## Testes locais e navegador

Regressão final **65passed em3,75s**, TEST_DATABASE_URL somente banco vazio visual_sessions_final no containerinstagram-link-m0-lifecycle-test127.0.0.1:55443. Inclui migrations001–006, cache29publicações paginado sem lacunas/duplicação, cursores inválidos/de outra conta negados, provider cursor criptografado, concorrência de sync e criação, organização/conta/produto/publicação, versões imutáveis e regressões M0/OAuth/HMAC/deduplicação. Provider real não é usado nessa suíte. Primeira execução encontrou fixture que ainda estava expirada após teste deliberado de token: reconexão sintética acrescentada antes de criar draft. Regressão repetida em banco vazio, passou.

`validate-publication-picker.cjs`: passou Admin e Operador, primeira etapa sem dropdown/IDs, miniaturas, configuração progressiva, troca de publicação preservando campos, paginação local+provider até37cards, automação existente abrindo edição, troca de conta sem mistura, AxeAA sem violações detectadas em320/390/768/1440. Capturas/trace somente fictícios. `validate-catalog.cjs` e `validate-operator.cjs` passaram regressões administrativas/operacionais, piloto/simulação/histórico/logout/CSRF/cache/OAuth simulado. Primeiros seletores de testes adaptados aos rótulos reais novos, sem afrouxar permissão.

Skills baseline-ui e design-ux utilizadas. Juiz independente da implementação inspecionou renders e encontrou major: formulário longe após grade longa. Corrigido recolhendo grade e mantendo resumo/Trocar publicação; preservação de campos acrescentada. Reavaliação confirmou major resolvido e nenhum blocker/major no escopo. Título após escolha melhorado para Configure sua automação. Capturas móveis recapturadas por viewport/foco adequado para remover artefato documental de skip-link. Isso não equivale a conformidade WCAG integral nem ensaio em celular físico.

`validate-session-preservation.cjs` passou: falha/recovery em segundo plano mantém campos; contexto reaberto com cookie próprio e ida/volta à política preservam login;503 na sessão ou vínculo mostra retry sem pedir senha; Sair explícito continua invalidando acesso. Sessões/tokens Supabase são simulados no browser; SQL testa refresh real local com provider fake.

Node--check, compileall, diff--check e caminhos de nove imagens do manual passaram. Capturas de manual usam fixture; nenhum dado pessoal ou credencial real incluído.

## Sessão: correções sem interromper a usuária

Já existia cookie persistente/refresh no servidor. Caminhos corrigidos: access_token recusado antes do timestamp local agora tenta refresh uma vez; rotação é persistida antes de segunda verificação de identidade para sobreviver a falha temporária. Backend segue verificando identidade e revogação. UI mostra restauração inicial, diferencia503temporário de401, verifica retorno de visibilidade/BFCache em background e mantém editor/campos para mesma identidade. Não chama location.reload nem logout ao navegar. O prazo absoluto não mudou. Causa exata no navegador da usuária não foi capturada com sua sessão; não foi solicitada senha ou reproduzido login real em nome dela.

Nenhuma aba da usuária foi recarregada/desconectada. API foi substituída com encerramento gracioso e mesmo túnel; sessões existentes continuam no banco. Testes de fechar/reabrir/atualizar página ocorreram somente em fixture, nunca no navegador real em uso.

## Teste com publicações reais e bloqueio externo

A conta já estava `reconnect_required` antes da consulta desta sessão. Nova consulta oficial media recusada por permission_denied. Repetição com EXATAMENTE os campos mínimos antigos também retornou HTTP400/código200 de permissão: não é evidência de falha específica de miniaturas. Nenhum token/status de conexão alterado, nenhuma reconexão/refresh/revogação ou DM executados para contornar.

Cinco publicações reais em cache foram percorridas em páginas de2por Admin e Operador reais do vínculo, sem lacunas ou acesso cruzado. Snapshot privado0600 dessas publicações alimentou somente uma fixture de renderização; navegador exibiu5cards e resumo da escolhida. Não foi login real, não grava campanha real e não homologa busca nova da Meta. Novas miniaturas e continuação externa real dependem da permissão/autorização da conta; testadas com provider fake. Não afirmar homologia externa concluída.

Docs oficiais Meta foram consultados; endpoints de referência retornaram429/indisponíveis à ferramenta. Não foi usada fonte secundária para prometer compatibilidade de campos. Campos opcionais tratados como opcionais e fallbacks; comprovação externa deles permanece pendente. Fonte de referência pretendida: https://developers.facebook.com/docs/instagram-platform/reference/instagram-media .

Comparação privada antes/depois confirmou env, memberships, credentials, contas (campos funcionais), produtos, campaigns/campaign_versions e tentativa M0 idênticos. Publicações cache preservadas;6migrations rastreadas. Estado geral e todas as contas reais pausados. Check-public pós-deploy passou HTTPS cockpit/privacy200,401sem sessão,403origem adversa e Axe móvel. Nenhuma mensagem enviada, nenhuma campanha piloto ativa e nenhum gate M0/SaaS declarado concluído.

A inspeção adicional da captura móvel identificou overflow programático provocado pela posição estática de labels/legends ocultos (sr-only) fora do shell. Ancoragem desses elementos e containing block do shell corrigidos; adicionada asserção de scrollHeight<=innerHeight/scrollY0 no runner móvel. Atualização apenas de CSS da página, sem recarga forçada de abas reais. Capturas e resultados finais constam no handoff.
