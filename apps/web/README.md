# Preparação da autenticação do cockpit — M0

`auth.ts` oferece login por senha, renovação e logout no Supabase Auth, consulta de identidade/autorização no FastAPI e início do Instagram Login. O componente visual React ainda não foi criado. O cockpit inicial está servido pelo FastAPI em `/m0/connect`, com HTML/CSS/JavaScript nativos em apps/api/pages e apps/api/assets. Este módulo TypeScript continua separado e não é o runtime dessa página. Consulte docs/17-SISTEMA-VISUAL-E-COCKPIT.md.

Injete somente SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY e a URL pública da API no cliente. Nunca injete DATABASE_URL, chave de criptografia ou App Secret. Mantenha a sessão em memória no protótipo; ao montar SSR/cookies persistentes, implemente sessão e CSRF adequadamente. Use sessão recém-renovada ao chamar o backend. Este verifica o token por GET /auth/v1/user, sem confiar em JWT apenas decodificado ou user_metadata para papéis.

Convide/crie o usuário pelo painel Supabase Auth. O primeiro vínculo é criado pelo comando administrativo de bootstrap documentado no README. Usuário autenticado sem membership recebe 403. O frontend não cria organizações nem atribui papéis por conta própria.

Para OAuth, hospede cockpit e API na mesma origem via proxy, ou sob o mesmo site HTTPS com CORS limitado a PUBLIC_APP_URL. O cookie de vinculação é Secure, HttpOnly e SameSite=Lax; não funciona em HTTP local nem se deve depender de cookies de terceiros entre sites distintos. O retorno ao cockpit recarrega a página; reautenticação pode ser necessária enquanto a sessão só estiver em memória.

O módulo TypeScript ainda não está integrado a um build/frontend e não foi homologado em navegador. A validação desta sessão cobre o backend e as respostas simuladas, não um login real de usuário.

## Atualização — sessão funcional no cockpit FastAPI

A página nativa atual usa a sessão server-side descrita em docs/18-COCKPIT-FUNCIONAL-E-PREPARACAO-PILOTO.md: cookie __Host-cockpit HttpOnly/Secure/Lax, Supabase access/refresh tokens Fernet no banco, refresh serializado, getUser por API e CSRF/origem em mutações. O módulo auth.ts acima permanece legado não integrado; não usar sua estratégia de memória como contrato da página atual. Uma futura migração React deve preservar esses endpoints e controles ou implementar solução equivalente revisada.
