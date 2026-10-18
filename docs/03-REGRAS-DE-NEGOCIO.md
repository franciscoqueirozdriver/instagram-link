# 03 — Regras de negócio e máquina de estados

## Elegibilidade, em ordem

1. Origem autenticada, conta reconhecida e evento suportado.
2. Comentário pertence a mídia própria selecionada; excluir próprios comentários e eventos de remoção. Respostas aninhadas fora do MVP, com motivo unsupported_nested.
3. Conta conectada; sistema e campanha ativos; publicação dentro da vigência.
4. Timestamp confiável. Se ausente, consultar metadado compatível; se não confirmado, não enviar.
5. Comentário criado após activated_at e dentro do período da campanha. Não enviar retroativamente por padrão.
6. Palavra ou frase corresponde à regra vigente.
7. Comentário sem envio aceito, em voo ou incerto registrado.
8. Opt-out aplicável ausente; política de frequência satisfeita.
9. Idade inferior à janela externa configurada e validada. Valor inicial: 7 dias; margem operacional de 5 minutos. Revalidar imediatamente antes de enviar.
10. Credencial e orçamento de chamadas disponíveis.

A regra de plataforma permite uma resposta privada por comentário; adotamos ainda uma regra de produto: **uma resposta por pessoa por campanha em 24h**, quando o identificador estiver disponível. Ela reduz repetição e deve ser exibida na configuração. Quando faltar ID do autor, manter deduplicação por comentário e registrar frequency_check_unavailable; não inventar identidade a partir do username. Revisar essa política no piloto.

## Gatilhos

Normalizar Unicode NFKC, casefold, espaços e pontuação. Padrão: palavra inteira; LINK e link! correspondem; linkado não. Frase: sequência contígua de tokens, como QUERO O LINK. Não aplicar remoção de acentos sem opção explícita. Vários gatilhos em uma campanha são OR. Regras ambíguas não causam múltiplas mensagens. Comentários editados não disparam novo envio no MVP.

## Campanhas e mensagens

Estados: draft → active ↔ paused → archived. Arquivada não reabre; duplicar como novo rascunho. Ativação exige mídia própria, produto ativo, link válido, mensagem renderizada, token e permissões válidos, prova de integração registrada e ausência de campanha concorrente.

Cada alteração cria campaign_version imutável. Ao pausar, jobs ainda não despachados ficam held. Ao retomar, cancelar jobs de versão antiga e não enviar backlog automaticamente; opção explícita de reavaliar apenas comentários da versão atual, ainda elegíveis. Não reassociar silenciosamente comentário a produto alterado.

Variáveis permitidas: {{product_name}} e {{product_links}}. Campos externos nunca viram código/template executável. Mensagem deve conter os links já na primeira resposta; não depender de segundo envio automático. Tamanho máximo configurado no adaptador conforme a versão Meta homologada; ativação bloqueia se a renderização ultrapassar o limite validado. Link de afiliado pode exigir identificação publicitária; o operador é responsável por revisar conteúdo e termos do programa.

## Estados de processamento

| Estado | Significado | Próximos estados |
|---|---|---|
| received | Evento persistido | ignored, queued |
| ignored | Não elegível, motivo salvo | Terminal; reavaliação explícita cria decisão nova |
| queued | Pronto para avaliação pelo worker | held, sending, expired, cancelled |
| held | Pausa ou conexão suspensa | queued após revalidação explícita, cancelled, expired |
| sending | Reserva persistida antes do request | accepted, retry_wait, failed, unknown |
| retry_wait | Falha comprovadamente repetível | queued, expired, failed |
| accepted | API aceitou e retornou identificação | Terminal; não significa entregue/lido |
| unknown | Despacho pode ter ocorrido | accepted se comprovado, closed_unknown; sem resend no MVP |
| failed | Erro permanente ou tentativas esgotadas | Terminal; novo envio não liberado cegamente |
| expired | Fora da janela | Terminal |
| cancelled | Cancelamento local | Terminal |
| closed_unknown | Encerrado sem comprovação | Terminal; reserva antirreenvio preservada |

Não prometer transação atômica entre PostgreSQL e Meta. Se worker morrer em sending, lease vencida leva a unknown; nunca a queued automaticamente.

## Erros e limites

Limite oficial consultado: 750 private replies/h por conta profissional para posts/Reels. Configuração operacional inicial proposta: 600 tentativas/h, janela móvel, todas as instâncias compartilhando contador. Inclui retentativas de despacho; reconciliação/leitura têm orçamento separado. Outras ferramentas na conta também consomem capacidade externa e não aparecem necessariamente no contador local.

Rejeição explícita por limite → retry_wait com espera indicada pelo provedor e jitter; autenticação/permissão → held e alerta; janela expirada → expired; comentário indisponível → failed. Exceção de rede depois de possível despacho e 5xx sem garantia de não aceitação → unknown. Só repetir erro cuja semântica validada comprove não envio. Máximo proposto: 5 tentativas seguras; atraso exponencial 30s, 60s, 120s, 240s, 480s, ajustado por Retry-After e janela.

Nenhuma continuação de conversa é implementada. Se vier a existir, terá política e janela próprias, verificadas antes da implementação; o comentário sozinho não autoriza sequência promocional.
