# Sistema visual e cockpit do anunciante

## Direção e escopo

Por solicitação do usuário, estabelecer a base visual antes de expandir as telas. Direção: ferramenta de trabalho sóbria, clara e consistente, com destaque para a conta selecionada e para a pausa. Primeira entrega em `/m0/connect`: login administrativo, visão geral, contas/permissões e resultados do teste controlado. Sem campanhas fictícias ou métricas de produção. Não altera a homologação pendente do M0.

Skills consultadas/aplicadas: `baseline-ui` para hierarquia, espaçamento, estados e interações; `accessibility-compliance-accessibility-audit` para contraste/teclado/semântica; `browser-testing-with-devtools` para inspeção renderizada, usando Playwright/Chromium como ferramenta disponível. Avaliadas também design-taste-frontend (declara foco em landing/portfólio, exclui dashboards) e awwwards-ui-design (efeitos desnecessários para esta operação); não adotadas como sistema do cockpit.

## Tokens e componentes

Fonte única: `apps/api/assets/cockpit.css`. É um sistema próprio sobre os controles HTML nativos já utilizados no projeto, sem alegar implementar Fluent/Carbon/Radix. Manter a página nativa permite preservar a origem, CSP, sessão e retorno OAuth sem introduzir outro build nesta fase. React/TypeScript continua uma decisão do alvo arquitetural; o módulo auth.ts existente não é usado nesta página e não deve ser tratado como seu runtime.

| Papel | Token/valor |
|---|---|
| Fundo | canvas `#f5f6f2` |
| Superfície | surface `#ffffff` |
| Texto | ink `#192c26` |
| Texto secundário | muted `#59685f` |
| Ação/seleção | accent `#163d32` |
| Conexão/aceite | success `#245b40` sobre `#e9f0e9` |
| Pausa/incerteza | warning `#765113` sobre `#fff5dd` |
| Erro/falha | danger `#a13434` sobre `#fff0ef` |
| Foco | contorno `#ac601f`, 3px, separado do controle |
| Espaçamento | 4, 8, 12, 16, 24, 32, 48px |
| Cantos | controles 8px, painéis 12px |
| Tipografia | fontes de sistema locais; corpo 16px, títulos responsivos; números tabulares |

Cores de estado não substituem texto. Componentes compartilhados: painéis, tags semânticas, botões primário/secundário/texto, seletor de conta, lista de permissões, aviso persistente de pausa, aviso contextual, estados vazio/carregando/erro e linhas de histórico. Ação principal por contexto; sem animações decorativas, gradients ou fontes/telemetria externas.

## Responsividade como aplicativo

No celular (até767px), estrutura contida em 100dvh: marca e contexto de conta fixos no topo, navegação fixa na base, rolagem somente no main. Documento sem rolagem lateral/vertical, overscroll contido, safe-area inferior respeitada. Conta selecionada permanece visível durante a leitura. Não desabilitar zoom do usuário. Meta viewport inclui interactive-widget=resizes-content para navegadores compatíveis. Desktop usa navegação lateral e cabeçalho aderente.

Verificação automatizada em 320/375/390/768/1024/1440px, além de renderização HTTPS com emulação móvel390x844. Isso não equivale a ensaio em todos os dispositivos físicos, teclados virtuais, Safari/iOS ou tecnologias assistivas. Antes da publicação definitiva testar aparelhos reais, zoom e leitores de tela.

## Fluxos e segurança

- Login direto no Supabase Auth; backend continua verificando bearer e membership admin. Sessão atual em cookie seguro com renovação Supabase server-side; a descrição completa está no guia18.
- Conectar usa o fluxo existente; reconectar acrescenta account_id selecionado. Backend mantém validação de mesma identidade e state/cookie seguro de uso único.
- Pausar é POST autenticado, persistente e escopado à organização/conta. Não existe retomada nesta entrega.
- Histórico retorna no máximo50 registros do teste controlado da conta e somente status, contador e datas/HTTP. Não devolve tokens, texto, comentário, destinatário ou provider IDs.
- Aceito pela API não é entregue/lido; falha é rejeição; incerto pode ter enviado e não oferece retry. Consulta com erro mostra traço/indisponível, nunca zeros falsos. Troca de conta descarta resultados antigos por geração de request.
- Dados de conta entram no DOM por textContent/Option; nenhum HTML vindo da conta é interpolado. CSP nonce permanece. Apenas a chave pública Supabase vai ao browser.

## Preparação PWA e lojas

Manifesto `/manifest.webmanifest`, display standalone, start_url `/m0/connect`, ícones192/512 e tema. Service worker `/service-worker.js` em HTTPS/localhost. Cache restrito a `/offline` e ícones: API, login, OAuth, webhook, cockpit HTML e dados privados nunca entram no cache. Navegação ao cockpit sem rede pode exibir fallback público; ações offline indisponíveis. Instalação oferecida quando beforeinstallprompt estiver disponível; em outros navegadores depende da opção nativa de adicionar à tela inicial.

Lojas ficam para etapa posterior por instrução explícita. Nenhum wrapper, conta de loja, certificado, pacote nativo ou submissão criado. Domínio HTTPS temporário serve homologação; URL/origem estável é necessária antes de distribuir instalação definitiva. Futuro empacotamento deve revisar deep links/callbacks, armazenamento seguro de sessão, requisitos de privacidade e testes físicos sem enfraquecer OAuth/HMAC.

## Reprodução dos testes renderizados

As ferramentas de teste ficam isoladas em /tmp, sem dependência no runtime do produto:

```bash
npm install --prefix /tmp/instagram-link-ui-tools playwright@1.56.1 @axe-core/playwright@4.10.2
.venv/bin/python -m uvicorn scripts.ui.fixture_server:app --host 127.0.0.1 --port 8011 --no-access-log
# Em outro terminal, usando o PID emitido por ESSE servidor fictício:
NODE_PATH=/tmp/instagram-link-ui-tools/node_modules UI_FIXTURE_PID=PID_DO_SERVIDOR_FICTICIO node scripts/ui/validate.cjs
```

O runner usa Chromium local no caminho definido no arquivo; ajustar para o executável instalado ao reproduzir em outro ambiente. A versão atual do runner deve ser usada conforme guia18 e a fixture parada separadamente. A prova histórica de fallback desligou somente a origem fictícia, nunca a API real. O teste percorre login/erro, seleção, reconexão vinculada, pausa, estados, teclado, contraste/auditoria Axe AA, larguras e cache/offline. Transporte Auth e dados de contas são sintéticos nesse servidor isolado; não é nova prova OAuth ou DM. Capturas em docs/ui contêm somente dados fictícios. Não iniciar fixture_server em produção.

Atualização funcional posterior: produtos, campanhas, versões, sessão persistente e revisão do piloto seguem os mesmos tokens visuais; consulte docs/18-COCKPIT-FUNCIONAL-E-PREPARACAO-PILOTO.md.
