# 05 — Modelo de dados lógico

> Atualização de escopo (16/10/2026): configuração por variáveis e gestão de múltiplas contas fazem parte do MVP. Consulte [a diretriz vigente](../docs/15-CONFIGURACAO-E-MULTIPLAS-CONTAS.md), que prevalece sobre referências anteriores a conta única. Implementação e contratos executáveis ainda pendentes.

Schema proposto para PostgreSQL; documento de modelagem, não migration executável.

| Entidade | Campos principais | Restrições |
|---|---|---|
| organizations | id UUID, name, timezone, paused_at | timezone IANA |
| users | id UUID, auth_subject, email, status | auth_subject único |
| memberships | organization_id, user_id, role | chave composta; admin/operator/viewer |
| instagram_accounts | id, organization_id, ig_user_id TEXT, username, connection_status, expires_at, scopes JSONB | UNIQUE(ig_user_id) no MVP |
| credentials | account_id, encrypted_token, key_version, refreshed_at | acesso somente do serviço; nunca retornar via API |
| products | id, organization_id, name, description, status | ativo/inativo |
| shopee_organization_credentials | organization_id, encrypted_credentials, configured_by, configured_at, updated_at | um conjunto criptografado por organização; grants públicos revogados; configuração somente Admin |
| product_links | id, product_id, label, url, position | HTTPS; ordem única por produto |
| media | id, account_id, ig_media_id TEXT, type, permalink, timestamp | UNIQUE(account_id, ig_media_id) |
| campaigns | id, organization_id, account_id, media_id, name, state, current_version_id, activated_at, starts_at, ends_at | índice único parcial por mídia WHERE state='active' |
| campaign_versions | id, campaign_id, version, keywords JSONB, match_mode, product_snapshot JSONB, template, rendered_message, created_by, created_at | UNIQUE(campaign_id, version); imutável |
| webhook_envelopes | id, received_at, body_hash, encrypted_payload, processing_state | payload com TTL curto |
| comment_events | id, envelope_id, account_id, event_key, comment_id TEXT, media_id, author_ref, text, occurred_at, received_at, event_type | UNIQUE(account_id,event_key) |
| decisions | id, event_id, campaign_version_id, outcome, reason_code, evaluated_at | append-only |
| dispatches | id, account_id, comment_id TEXT, campaign_version_id, status, expires_at, provider_message_id, attempt_count, lease_until, next_attempt_at, unknown_reason | UNIQUE(account_id,comment_id) |
| attempts | id, dispatch_id, started_at, finished_at, outcome, http_status, provider_error_code, provider_trace_id | imutável; sanitizar detalhes |
| rate_reservations | id, account_id, attempt_id, reserved_at | índice account_id,reserved_at; limpeza >24h |
| recipient_cooldowns | account_id, campaign_id, author_ref, last_reserved_at, dispatch_id | UNIQUE(account_id,campaign_id,author_ref) |
| suppressions | organization_id, account_id, subject_hash, reason, created_at | consulta antes de enfileirar |
| audit_logs | id, organization_id, actor_id, action, target_type, target_id, diff_safe JSONB, created_at | append-only; sem token ou texto desnecessário |
| deletion_requests | id, organization_id, subject_ref, status, requested_at, completed_at | rastrear exclusão sem reter conteúdo excluído |

## Integridade

FKs devem garantir mesma organização e conta entre mídia, campanha e produto; usar chaves compostas ou validação transacional com testes de acesso cruzado. product_snapshot armazena nome e links da versão, evitando que editar produto altere um job existente. Não usar username como chave estável.

Estado da conexão: pending, connected, expiring, reconnect_required, disconnected. Banco valida enum/check de estados e timestamps. Todas as tabelas operacionais usam created_at/updated_at em timestamptz. Migrações forward-only com plano de correção; não apagar tabelas para rollback de código.

## Retenção proposta, sujeita à revisão do responsável

Payload bruto criptografado: 7 dias; texto de comentário: 30 dias; detalhes de tentativa: 90 dias; agregados sem identificação: 12 meses; auditoria administrativa sanitizada: 12 meses. Backup: 30 dias com rotação. Não registrar corpo de DM em logs gerais.

A chave antirreenvio precisa sobreviver ao descarte de texto: manter identificador mínimo até 30 dias após terminar a janela de envio, depois apagar ou pseudonimizar. Em pedido de exclusão, remover dados pessoais e preservar apenas marcador HMAC mínimo de supressão quando houver fundamento documentado; não declarar hash anonimização automática. Reaplicar exclusões ao restaurar backup. Política final depende de finalidade e base legal revisadas.

## Consulta de fila

Índice parcial (status,next_attempt_at,expires_at) para queued/retry_wait; lease com duração superior ao timeout total de transporte e renovação controlada. Reaper converte sending abandonado em unknown. Lock por conta coordena limite móvel e pausa. Cooldown é reservado atomicamente com dispatch; em falha comprovada sem envio pode ser liberado conforme regra, mas unknown preserva reserva.

## Entidades de suporte aos contratos

Adicionar admin_idempotency_keys (organization_id, actor_id, method, route, key, request_hash, response_safe, expires_at), com unicidade pelo escopo completo; sessões/convites conforme provedor de auth; import_jobs para sincronização de mídia. products.version suporta expected_version; campaigns.current_version_id resolve o número da versão. Alteração de estado exige expected_version e lock, sem criar nova versão de conteúdo se só pausar. Chaves de idempotência não guardam resposta contendo credencial.
