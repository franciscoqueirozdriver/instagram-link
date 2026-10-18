"""Instagram long-lived token maintenance; never sends messages."""
from datetime import timedelta

import httpx


class TokenLifecycleError(Exception):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def refresh_eligibility(issued_at, expires_at, now, scopes):
    if expires_at is None or expires_at <= now:
        return 'expired'
    if 'instagram_business_basic' not in scopes:
        return 'missing_permission'
    if issued_at is None or now - issued_at < timedelta(hours=24):
        return 'too_young'
    return 'eligible'


def checked_payload(response):
    try:
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError()
        code = body.get('error', {}).get('code') if isinstance(body.get('error'), dict) else None
        if response.status_code == 401 or code == 190:
            raise TokenLifecycleError('reconnect_required')
        if response.status_code == 403 or code in (10, 200):
            raise TokenLifecycleError('permission_denied')
        if response.status_code != 200 or 'error' in body:
            raise TokenLifecycleError('provider_unavailable')
        return body
    except (ValueError, TypeError):
        raise TokenLifecycleError('invalid_response') from None


async def refresh_token(settings, snapshot, now, client):
    reason = refresh_eligibility(snapshot['refreshed_at'], snapshot['expires_at'], now, snapshot['scopes'])
    if reason != 'eligible':
        raise TokenLifecycleError(reason)
    try:
        response = await client.get('https://graph.instagram.com/refresh_access_token', params={
            'grant_type': 'ig_refresh_token', 'access_token': snapshot['token']})
        body = checked_payload(response)
        token, expires = body.get('access_token'), body.get('expires_in')
        if not isinstance(token, str) or not token or type(expires) is not int or expires <= 0:
            raise TokenLifecycleError('invalid_response')
        profile = checked_payload(await client.get(
            'https://graph.instagram.com/' + settings.meta_api_version + '/me',
            params={'fields': 'user_id'}, headers={'Authorization': 'Bearer ' + token}))
        if str(profile.get('user_id')) != snapshot['ig_user_id']:
            raise TokenLifecycleError('identity_mismatch')
        return token, expires
    except httpx.HTTPError:
        raise TokenLifecycleError('transport_uncertain') from None
