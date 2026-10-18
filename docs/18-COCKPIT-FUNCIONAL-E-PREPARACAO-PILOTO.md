# Cockpit funcional, sessão e preparação de piloto

## Escopo autorizado

Em17/10/2026 o operador autorizou avançar produtos/links, campanhas por publicação, inclusão/exclusão de palavras-chave, mensagem com prévia e histórico, preservando pausa geral. Autorizou corrigir sessão após OAuth e pediu análise do impacto das pendências M0. Esta instrução permite desenvolver o cockpit enquanto verificações externas continuam; não autoriza DM, ativação geral nem declaração de M0 homologado. Nenhuma campanha real deve ser inventada com links ou produto presumidos.

Acesso atual: https://raises-formula-parameter-muslim.trycloudflare.com/m0/connect. Túnel temporário; manter origem enquanto estiver configurada na Meta. Lojas seguem adiadas. Layout móvel continua como aplicativo: contexto e navegação fixos, rolagem interna, sem deslocamento lateral.

## Fluxo disponível

1. Entrar uma vez na nova versão com usuário Supabase administrativo. A sessão agora permanece em recargas e retorno do Instagram, até seu prazo/revogação.
2. Produtos: cadastrar nome, descrição interna e1–5 links HTTPS com rótulos; ordenar, editar, remover links e inativar produto. Campanhas preservam cópia do produto da sua versão.
3. Campanhas: selecionar conta, sincronizar publicações próprias, escolher publicação/produto e cadastrar inclusão/exclusão. Palavra/frase inteira, NFKC/casefold; exclusão prevalece; ignorar acentos é opção explícita.
4. Mensagem: usar somente {{product_name}} e {{product_links}}, com links obrigatórios. Prévia textual e contagem UTF-8; servidor valida o limite configurado (atual1000bytes). Nada executa HTML/template arbitrário.
5. Salvar rascunho; alterações criam versões imutáveis. Editar catálogo não altera versões salvas. Arquivar campanha preserva histórico e impede reabertura.
6. Preparar piloto: escolher UMA campanha, testar comentário positivo/negativo e analisar comentários próprios da publicação. Nenhuma tentativa de mensagem é criada. Revisão contém regra/versão/mensagem, comentários analisados, pré-elegibilidade e razões de exclusão.
7. Histórico: consultar resultados do teste privado anterior, alterações de campanha, versões completas e análises salvas. Revisão vencida ou de versão alterada é sinalizada; não oferece reenvio.

A sincronização consulta até3páginas de25 mídias/comentários, com cursor e host fixo. Mais registros são explicitamente parciais. Na conta real foram sincronizadas5publicações e validada a consulta de4comentários de uma publicação; nada enviado. Não significa que cada publicação tenha4comentários. O produto/link/publicação do piloto real ainda depende da escolha do operador, solicitada durante o trabalho; dados sintéticos das capturas não foram cadastrados na organização real.

## Sessão Supabase Auth no backend FastAPI

Mecanismo BFF: login por senha encaminhado ao Supabase Auth; access/refresh tokens ficam Fernet no banco privado cockpit_sessions, ligados ao usuário. Cookie __Host-cockpit contém somente identificador aleatório, cujo SHA256 é armazenado no banco; atributos HttpOnly/Secure/SameSite=Lax/Path=/, sem Domain. JavaScript recebe apenas identidade e CSRF, sem JWT/refresh token ou localStorage.

Cada operação resolve a sessão e verifica identidade por GET /auth/v1/user do Supabase, sem confiar em JWT apenas decodificado. Perto da expiração do access token, usa grant_type=refresh_token e salva o par renovado. Lock de linha serializa rotação entre abas/processos. Erros não viram sessão válida. Restauração após reinício depende do banco e da mesma chave Fernet, não de memória do processo.

POST/PUT/DELETE autenticados por cookie exigem Origin exata e X-CSRF-Token da sessão; login também exige origem correta. Login sem papel admin é negado. Logout remove sessão local, solicita signout Supabase scope=local, limpa cookie da sessão e o vínculo OAuth pendente. O logout local continua efetivo se o serviço remoto não responder. Bearer explícito de clientes existentes mantém verificação anterior; não é autenticação por cookie ambiente.

COCKPIT_SESSION_SECONDS configura duração máxima absoluta (padrão604800segundos, sete dias; entre300 e2592000). Não altera prazo/revogação do Supabase e não agenda expurgo automático. Não foram alteradas senhas nem chaves existentes. Respostas privadas e com cookies usam Cache-Control: private,no-store. Service worker permanece sem cache de login, API, cockpit HTML ou dados de conta.

Referências oficiais: [sessões Supabase](https://supabase.com/docs/guides/auth/sessions), [server-side Auth](https://supabase.com/docs/guides/auth/server-side/advanced-guide), [refresh session](https://supabase.com/docs/reference/python/auth-refreshsession). Não se afirma usar @supabase/ssr (pacote JavaScript); este backend Python implementa a ponte ao protocolo Supabase Auth com armazenamento server-side.

## Três estados distintos

| Estado | Significado | Impacto |
|---|---|---|
| Conta conectada | OAuth válido, credencial e permissões registradas | Permite consultas e preparação; não liga automação |
| Automação pausada | Decisão operacional global/da conta | Nenhum envio geral; preparar revisão não retoma |
| Identificação do app na assinatura pendente | Solicitação comments aceita, comparação de Application ID ainda não resolvida | Pendência de atribuição/auditoria; não tratar como token inválido nem como falha geral da conexão |

O verificador de assinatura HMAC dos POSTs continua obrigatório e independente dessa associação de identificador. Não alterar chaves ou aceitar HMAC inválido para remover o aviso. UI não apresenta inscrição accepted como mensagem aceita/entregue.

## Regras e limites da revisão

Consulta somente mídias próprias via token da conta. Para pré-elegibilidade exige autor/comentário identificados, comentário visível e de nível superior, autor diferente da própria conta, timestamp confiável, regra positiva sem exclusão, janela inferior a7dias com5min de margem, ausência de tentativa anterior e no máximo um comentário por autor no conjunto analisado. Metadado de visibilidade ausente bloqueia. Comentários anteriores ao cadastro da campanha são excluídos na revisão; ativação futura deve estabelecer novo corte, sem backfill automático.

A prévia NÃO é uma reserva de envio ou prova de elegibilidade futura. IDs/textos da análise ficam criptografados e só admin da organização/conta pode reabrir. Validade técnica15min; não promete eliminação automática. Versão nova, campanha arquivada ou prazo vencido exigem reanálise. Não existe endpoint para ativar/envio nesta entrega; estado de campanha limitado a draft/paused/archived e Settings recusa pausa global false.

## O que bloqueia um piloto e o que não bloqueia desenvolvimento

| Item | Situação / impacto |
|---|---|
| Autorização para envio e configuração do piloto | Bloqueio deliberado atual. Falta escolher produto/links/publicação/regras reais e revisar uma campanha específica. Nenhuma liberação presumida. |
| Despachante de campanhas | Bloqueio técnico para ativação automática: ainda não há fila/lease de campanhas, reserva compartilhada de orçamento/cooldown, suppression/opt-out operacional e recuperação unknown por campanha. A ferramenta da única DM M0 NÃO pode ser reutilizada como worker ou novo grant. |
| Evento real na origem HTTPS atual | Verificação externa obrigatória antes da primeira liberação: webhook GET novo foi salvo, mas POST comments/HMAC deve ser observado/correlacionado no endereço novo. Prova real histórica existe; não foi apagada. Pedir comentário controlado somente após definir piloto; sem DM. |
| Refresh Instagram real | Teste ainda pendente; token atual válido e consultas reais funcionam. A tentativa age-gated nesta sessão pulou refresh, pois idade local conservadora<24h. Primeiro horário elegível calculado18/10/2026 09:59:34 Brasília. Não bloqueia cadastro/revisão ou por si só invalida credencial atual; automação contínua depende de manutenção e alerta. |
| Revogação externa seguida de recuperação | Teste real pendente e requer operador para retirar/restaurar autorização. Código190/permissões pausar somente a conta é testado localmente e aplicado nas consultas de catálogo; reconexão normal real já ocorreu. Não revogar silenciosamente a credencial de trabalho. |
| Application ID da inscrição | Pendência de identificação/auditoria; não existe prova de token inválido ou motivo para paralisar o catálogo. Antes de concluir M0, relacionar IDs corretamente com dados oficiais do app. Se houver divergência de emissor/assinatura real, isso se torna bloqueio técnico. |
| Domínio estável, instalação/teclado real, expurgo e backup/restore | Pendências operacionais/produção. DNS temporário já falhou antes e é risco concreto; necessário estabilizar antes de distribuição/operação contínua. Não impede trabalhar no cockpit local/HTTPS de homologação. |

Para piloto supervisionado, refresh/revogação externos são verificações ainda não concluídas; não alegar homologação integral a partir de mocks. O token saudável de hoje não substitui esses testes. Pendências não justificam bloquear evolução independente, e essa evolução não autoriza enviar sem controles.

## Testes e reprodução

```bash
.venv/bin/python -m pytest -q
# Banco descartável vazio APENAS:
TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55443/BANCO_VAZIO .venv/bin/python -m pytest -q
# UI isolada, sem dados/token reais:
.venv/bin/python -m uvicorn scripts.ui.fixture_server:app --host 127.0.0.1 --port 8011 --no-access-log
NODE_PATH=/tmp/instagram-link-ui-tools/node_modules node scripts/ui/validate.cjs
# Somente páginas públicas do HTTPS real:
UI_PUBLIC_URL=https://raises-formula-parameter-muslim.trycloudflare.com NODE_PATH=/tmp/instagram-link-ui-tools/node_modules node scripts/ui/check-public.cjs
```

Ferramentas Playwright/Axe continuam em /tmp e Chromium no caminho do runner. A fixture usa somente dados sintéticos e pode ser resetada por endpoint exclusivo dela; nunca executá-la em produção. Parar a fixture separadamente após o teste. O script verifica cookie persistente depois do retorno OAuth simulado, catálogo/regras/prévia/revisão/histórico, CSRF/logout/cache e seis larguras com Axe AA. OAuth completo/senha de usuário real não foram automatizados pelo agente. Aprovação automatizada não comprova Safari/teclado físico ou WCAG integral.

Migration005 foi validada em PostgreSQL descartável antes de aplicar ao Supabase. Todas15tabelas têm RLS e nenhuma permissão de schema/tabela para anon/authenticated. Política pública revisada para refletir senha via backend, sessão persistente e análise criptografada; retenção continua sem expurgo automático.
