# 06 — Configuração Meta e prova de integração

> Atualização de escopo (16/10/2026): configuração por variáveis e gestão de múltiplas contas fazem parte do MVP. Consulte [a diretriz vigente](../docs/15-CONFIGURACAO-E-MULTIPLAS-CONTAS.md), que prevalece sobre referências anteriores a conta única. Implementação e contratos executáveis ainda pendentes.

## Modalidade escolhida

Instagram API with Instagram Login. Conta Business/Creator; essa modalidade não exige Página vinculada. Não misturar os scopes instagram_business_* com o fluxo Facebook Login. Fontes e limitações da consulta em 14-FONTES-E-VALIDACAO.md.

## Passo a passo para o administrador

1. Confirmar acesso administrativo à conta profissional e capacidade de conceder permissões. Separar conta e mídia de teste das campanhas reais.
2. Criar app no painel Meta e selecionar o caso de uso que disponibilize Instagram Login. Os nomes dos menus variam; não presumir que escolher apenas o tipo “Negócio” habilita tudo.
3. Registrar App ID e App Secret em cofre do backend. Cadastrar domínio, contato, política de privacidade, instrução/fluxo de exclusão e URI de callback HTTPS exata.
4. Configurar Instagram Login; solicitar apenas instagram_business_basic, instagram_business_manage_comments e instagram_business_manage_messages conforme requisitos atuais dos endpoints. Não solicitar publicação, anúncios ou insights sem necessidade.
5. Configurar papéis/testadores e aceitar convites exigidos. O nível Standard atende contas próprias/geridas quando elegíveis; contas de terceiros requerem avaliar Advanced Access e App Review. Modo de desenvolvimento não é atalho para operar livremente contas de clientes.
6. Executar autorização OAuth com state aleatório, de uso único, associado à sessão e TTL de 10 min. Trocar code no backend. Não registrar code, token ou URL sensível em logs. PKCE se suportado pelo fluxo escolhido e documentado na implementação.
7. Consultar identidade autorizada, conferir permissões efetivas e salvar token criptografado. Registrar expires_in/expiração real; não presumir token eterno ou validade universal de 60 dias.
8. Configurar callback público GET/POST /webhooks/instagram e verify token independente do App Secret.
9. GET de verificação deve validar hub.mode e hub.verify_token e devolver hub.challenge como texto; falha retorna 403. Esse handshake não autentica os POSTs.
10. Nos POSTs, validar X-Hub-Signature-256 com HMAC-SHA256 do corpo bruto usando App Secret e comparação em tempo constante.
11. Assinar o campo de comentários apropriado e a conta autorizada conforme o procedimento da modalidade. Registrar evidência da assinatura; botão de evento sintético não comprova evento real.
12. Importar mídias próprias e identificar o IG media ID, não o shortcode da URL. Percorrer paginação.
13. Criar comentário real autorizado com a palavra-chave e verificar o evento recebido, identificação da mídia, autor quando disponível e timestamp.
14. Fazer um único private reply de teste para aquele comentário. Registrar request sanitizado, versão, retorno e message_id. Verificar manualmente a DM no Instagram.
15. Reentregar o evento e reiniciar worker. Comprovar que não sai segunda tentativa.
16. Testar revogação/reconexão e expiração simulada; somente depois habilitar campanha piloto.

## Contrato de envio escolhido

POST https://graph.instagram.com/{META_API_VERSION}/{IG_USER_ID}/messages
Authorization: Bearer <token no backend>
Content-Type: application/json

```json
{"recipient":{"comment_id":"COMMENT_ID"},"message":{"text":"Olá! Aqui está o link solicitado: https://shopee.com.br/EXEMPLO"}}
```

Este é o contrato alvo a homologar para Instagram Login; não usar /{IG_USER_ID}/private_replies. Verificar path, versão e scopes no app antes do primeiro envio. Não fixar v22.0 por cópia do protótipo: selecionar uma versão suportada no painel, registrar em ambiente e executar teste de contrato. Até isso ocorrer, integração permanece não homologada.

## Campos e metadados

Não reutilizar created_time por suposição. Validar os campos de comentário disponíveis na versão e modalidade; normalizar timestamp e autor em contrato interno. Se webhook não trouxer tudo, completar por consulta autorizada; indisponibilidade impede envio, não libera fallback inseguro.

## Renovação e acesso a terceiros

Job diário verifica expiração; renovar antecipadamente conforme o fluxo documentado, sem expor segredo no frontend. Testar validade mínima e condições de renovação da modalidade no gate técnico. Reautorização necessária se escopo mudar ou token for revogado. Pausar antes de expirado; alertas propostos com 7 e 2 dias restantes.

Para servir clientes: tratar Advanced Access, revisão de permissões, evidência em vídeo, instruções ao revisor, verificação de negócio quando exigida, exclusão de dados e suporte. Prazo de aprovação externo não faz parte da estimativa de programação.

## Evidências obrigatórias

Conta/ID mascarado; modalidade; API version; scopes concedidos; acesso Standard/Advanced; data de validação; endpoint sanitizado; webhook real autenticado; aceite com message_id; captura manual da DM para revisão interna; duplicidade bloqueada; pausa; renovação; revogação. Nenhuma credencial deve aparecer no relatório.
