# 08 — Segurança e privacidade

## Controles obrigatórios

- HTTPS, cookies HttpOnly/Secure/SameSite, expiração de sessão, proteção CSRF em operações com cookie e limitação de tentativas de login.
- Preferir provedor de autenticação gerenciado; se senha própria, Argon2id e fluxo seguro de recuperação. MFA administrativo desejável para produção.
- RBAC e organization_id verificados no backend em toda operação; IDs enviados pelo cliente não estabelecem autorização.
- OAuth state aleatório, único e com TTL; callback exato; tokens apenas no serviço, criptografados com chave fora do banco e versionada.
- Credenciais Shopee Affiliate Open API são escopadas por `organization_id`, criptografadas com `TOKEN_ENCRYPTION_KEY` antes da persistência, retornadas somente pelo serviço e configuráveis apenas pelo Administrador da organização. A interface não lê de volta App Secret; a atualização exige os dois campos juntos. A tabela privada mantém RLS e sem grants para `PUBLIC`, `anon` ou `authenticated`.
- HMAC do corpo bruto do webhook; comparação constante; replay tratado por deduplicação. Verify token de handshake não substitui assinatura.
- Segredos nunca em Git, imagens, browser, URLs do painel, logs, exportações ou documentação. Sanitizar URLs de chamadas OAuth que precisem parâmetros sensíveis.
- Produtos aceitam somente HTTPS com hostname válido; rejeitar credenciais embutidas, javascript:, data: e URLs locais. Não buscar URL fornecida pelo operador no servidor no MVP; se futuramente houver preview, implementar defesa SSRF e redirecionamentos.
- Renderizar comentários como texto; consultas parametrizadas; validação de payload, limites de tamanho e dependências auditadas.
- Exportações protegem campos iniciados por =, +, -, @, tab e CR contra execução em planilhas.

## Matriz de ameaça

| Ameaça | Controle | Evidência |
|---|---|---|
| Webhook forjado | HMAC + conta/mídia conhecida | Teste de corpo adulterado |
| Token roubado | Cofre, criptografia, redaction e rotação | Inspeção de logs/bundle |
| IDOR | RBAC + escopo no servidor | IDs de organização distinta negados |
| Reenvio por concorrência | Unicidade + lease + unknown | Teste com dois workers e crash |
| Produto/link trocado | Versão imutável e snapshot | Job antigo preserva mensagem |
| Operador comprometido | Privilégio mínimo, auditoria, pausa | Trilhas e revogação de sessão |
| Backup com dados excluídos | Retenção e reaplicação de exclusões | Ensaio de restore |

## Tratamento de dados

Dados necessários: IDs de conta/post/comentário, identificador do autor quando disponível, texto do gatilho e resultado técnico. Não coletar email/telefone do comentarista. Finalidade: responder à solicitação contextual e operar o serviço.

O responsável pelo projeto deve definir controlador, operadores contratados, base legal adequada, aviso de privacidade, canal de direitos e transferência internacional. O comentário com palavra-chave não deve ser tratado como consentimento irrestrito para marketing futuro. Este documento é orientação técnica e minuta; não determina sozinho conformidade jurídica.

Retenção em 05-MODELO-DE-DADOS.md. Exclusão deve alcançar payloads, texto, tentativas identificáveis e exportações sob controle do serviço; backups saem pela rotação e restaurações reaplicam exclusões. Desconectar interrompe novos envios e elimina/revoga credencial conforme capacidade do provedor, sem alegar apagar DMs já recebidas no Instagram.

## Incidente

Pausar conta → revogar/rotacionar credenciais afetadas → preservar evidência sanitizada → identificar alcance → corrigir → testar reconexão → retomar de forma controlada. Avaliar obrigações de comunicação conforme fatos e regras aplicáveis, sem definir prazo legal por suposição.
