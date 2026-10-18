# Checklist de liberação

Preencher: responsável ___ • data ___ • commit ___ • ambiente ___ • API version ___

- [ ] Escopo MVP e decisões pendentes revisados.
- [ ] M0 aprovado com conta, scopes, webhook real e DM controlada.
- [ ] Limite da mensagem e unidade de medida homologados.
- [ ] Autenticação/RBAC/escopo e CSRF verificados.
- [ ] Banco privado, migrations e índices únicos aplicados.
- [ ] Assinatura do webhook validada sobre bytes originais.
- [ ] Testes T01–T30 aprovados, evidências e limitações registradas.
- [ ] Nenhum token em Git, browser, logs ou exportações.
- [ ] Limite compartilhado e outras ferramentas da conta inventariados.
- [ ] Pausa global e campaign version testadas.
- [ ] Timeout/crash não geram resend automático.
- [ ] Alertas de token, fila, unknown e backup testados.
- [ ] Backup restaurado e exclusões reaplicadas; RPO/RTO medidos.
- [ ] Política publicada com dados reais e canal de direitos funcional.
- [ ] Produto, links e mensagem da campanha revisados.
- [ ] Deploy/rollback ensaiados sem perder antirreenvio.
- [ ] Operador treinado e responsável por incidentes definido.
- [ ] Produção inicia pausada; ativar somente campanha piloto.

Resultado: ___ • Pendências bloqueantes: ___ • Evidências: ___ • Responsável pela liberação: ___
