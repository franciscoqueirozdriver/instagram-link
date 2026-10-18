/** M0 cockpit integration: use the Supabase session access token, never an API key
 * as proof of user identity. Call with a freshly obtained/refreshed Auth session.
 * The host cockpit owns Supabase signInWithPassword / refresh / signOut.
 */
export type SupabaseSession = { access_token: string };
export type CockpitUser = {
  user: { id: string; email: string | null };
  memberships: { organization_id: string; role: 'admin' | 'operator' | 'viewer' }[];
};

export async function loadCockpitUser(apiUrl: string, session: SupabaseSession): Promise<CockpitUser> {
  const response = await fetch(`${apiUrl}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
    cache: 'no-store',
  });
  if (!response.ok) throw new Error(response.status === 401 ? 'Sessão expirada' : 'Acesso indisponível');
  return response.json();
}

export async function connectInstagram(apiUrl: string, session: SupabaseSession, organizationId: string) {
  const response = await fetch(`${apiUrl}/api/v1/instagram/connect?organization_id=${encodeURIComponent(organizationId)}`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('Não foi possível iniciar a conexão Instagram');
  const data: { authorization_url: string } = await response.json();
  window.location.assign(data.authorization_url);
}

export type AuthSession = SupabaseSession & { refresh_token: string; expires_in: number };

export async function signInCockpit(supabaseUrl: string, publishableKey: string, email: string, password: string): Promise<AuthSession> {
  const response = await fetch(`${supabaseUrl}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: { apikey: publishableKey, 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('Não foi possível entrar no cockpit');
  return response.json();
}

export async function refreshCockpitSession(supabaseUrl: string, publishableKey: string, refreshToken: string): Promise<AuthSession> {
  const response = await fetch(`${supabaseUrl}/auth/v1/token?grant_type=refresh_token`, {
    method: 'POST',
    headers: { apikey: publishableKey, 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('Sessão expirada');
  return response.json();
}

export async function signOutCockpit(supabaseUrl: string, publishableKey: string, session: SupabaseSession) {
  const response = await fetch(`${supabaseUrl}/auth/v1/logout`, {
    method: 'POST',
    headers: { apikey: publishableKey, Authorization: `Bearer ${session.access_token}` },
  });
  if (!response.ok) throw new Error('Não foi possível encerrar a sessão');
}
