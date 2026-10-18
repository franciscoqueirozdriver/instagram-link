# 01 — Documento de produto

> Atualização de escopo (16/10/2026): configuração por variáveis e gestão de múltiplas contas fazem parte do MVP. Consulte [a diretriz vigente](../docs/15-CONFIGURACAO-E-MULTIPLAS-CONTAS.md), que prevalece sobre referências anteriores a conta única. Implementação e contratos executáveis ainda pendentes.

## Problema e resultado esperado

Quem divulga produtos precisa entregar o link correspondente a quem comenta uma palavra solicitada no post. O atendimento manual demora, perde comentários e pode enviar o produto errado.

O sistema deve permitir configurar a campanha e entregar uma resposta privada contextualizada, registrando o resultado para o operador. Exemplo: post de uma luminária, gatilho LINK, mensagem com o link daquela luminária. O mesmo seguidor pode pedir outro produto em outro post.

## Personas e permissões

| Papel | Responsabilidade |
|---|---|
| Administrador | Conectar/desconectar conta, usuários, segurança, configurações e campanhas |
| Operador | Produtos, campanhas, simulação, ativação, pausa e acompanhamento |
| Consulta | Painel e histórico sanitizado, sem exportar ou alterar |
| Comentarista | Interage no Instagram; não precisa criar conta na aplicação |

MVP com cadastro administrativo por convite. Sem registro público. Primeiro administrador criado por comando de bootstrap de uso único; proibir endpoint público para essa finalidade.

## Jornada principal

Administrador conecta conta → operador cadastra produto → seleciona post → define gatilho e mensagem → simula comentário → ativa campanha → usuário comenta → webhook é autenticado e persistido → worker decide elegibilidade → fila controla limite → Meta aceita envio → painel registra aceite.

Não chamar o aceite da API de entrega ou leitura. Mensagem aceita pode ir para solicitações e não ser vista. Cliques e vendas não são inferidos do aceite.

## Escopo MVP

Conta própria profissional; importação paginada dos próprios posts/Reels suportados; produtos com um ou mais links HTTPS; uma campanha ativa por mídia; regras por palavra inteira ou frase; mensagem fixa com variáveis limitadas; webhook; fila; auditoria; token e saúde da conexão; histórico filtrável; pausa global; exclusão de dados e backup.

Fora do MVP: Lives, anúncios, Stories, comentários de terceiros em posts alheios, conversação posterior, chatbot, campanhas em massa, resposta pública automática, seguir/curtir como requisito, coleta de telefone, métricas de venda, checkout, Shopee API, SaaS multiempresa e aplicativo de celular.

## Métricas propostas

- Tempo entre recebimento local e aceite da Meta: p95 ≤ 60 segundos sem fila por limite ou indisponibilidade; medir separadamente o atraso do webhook.
- Zero tentativas simultâneas para o mesmo comentário nos testes de concorrência.
- 100% das decisões com código de motivo e versão da campanha.
- Taxa de aceite = envios aceitos / tentativas enviadas; não confundir com conversão.
- Alertas para conexão inválida, falhas crescentes e fila próxima da expiração.

Metas são objetivos de engenharia, não SLA contratado. Definir linha de base no piloto.

## Critério de sucesso do piloto

Uma campanha real controlada, comentários de contas autorizadas pelo modelo de acesso da Meta, produto correto, sem reenvio após webhook repetido ou reinício, pausa funcionando e recuperação comprovada de backup. Expansão somente após cumprir os gates de homologação.
