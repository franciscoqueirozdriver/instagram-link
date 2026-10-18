# 07 — Telas e experiência

> Atualização de escopo (16/10/2026): configuração por variáveis e gestão de múltiplas contas fazem parte do MVP. Consulte [a diretriz vigente](../docs/15-CONFIGURACAO-E-MULTIPLAS-CONTAS.md), que prevalece sobre referências anteriores a conta única. Implementação e contratos executáveis ainda pendentes.

## Navegação

Painel • Campanhas • Produtos • Publicações • Histórico • Conexão • Configurações. Consulta vê somente Painel/Histórico sanitizado. Usuários e credenciais restritos ao administrador.

| Tela | Conteúdo e ações | Estados necessários |
|---|---|---|
| Login | Email/senha ou provedor administrativo escolhido; convite | Carregando, inválido, bloqueado, sessão expirada |
| Painel | Recebidos, elegíveis, aceitos, falhas, incertos, fila, saúde | Vazio orientado, erro, dados parciais |
| Produtos | Nome, descrição, links ordenados, ativo | URL inválida; produto usado por campanha |
| Publicações | Thumbnail quando autorizado, legenda resumida, data, permalink | Paginação, sem mídia, erro de permissão |
| Campanhas | Status, post, produto, gatilho, versão e vigência | Rascunho, ativa, pausada, arquivada |
| Editor | Selecionar post/produto, gatilhos, mensagem, simular | Preview exato renderizado; erro de tamanho |
| Histórico | Status, motivo, campanha, datas e tentativas | Aceito, incerto, expirado; filtros e cursor |
| Conexão | Conta, permissões, expiração e reconectar | Sem conexão, válida, expirando, revogada |
| Configurações | Usuários, frequência, retenção e pausa global | Negação por papel, confirmação de ação destrutiva |

## Editor de campanha

Etapas: publicação → produto/links → gatilho → mensagem → simulação → revisão/ativação. Exibir claramente que o sistema enviará uma única resposta privada com os links. Avisar que editar produto não modifica uma versão já ativa; oferecer criar nova versão e reativar.

Ativar requer simulação positiva e negativa. Exemplo positivo: “Quero o LINK!”; negativo: “ficou linkado”. Simulação não chama a Meta nem cria tentativa. Preview nunca interpola HTML executável.

Pausa global sempre visível para administrador/operador. Mensagem: “Novos envios pausados. Requisições já iniciadas podem concluir.” Retomada informa quantidade de jobs retidos e exige política explícita para backlog elegível.

## Linguagem de status

“API aceitou o envio” em vez de “Cliente recebeu”. “Resultado incerto — envio pode ter ocorrido; reenvio bloqueado” em vez de botão automático “Tentar novamente”. Exibir reason_code traduzido com detalhe sanitizado.

## Acessibilidade e responsividade

Operação em desktop e celular; tabelas com rolagem e alternativa compacta. Foco visível, botões com rótulo, alertas anunciáveis, formulários com erros associados. Datas com fuso mostrado; períodos no painel calculados no timezone da organização e convertidos para UTC na API.
