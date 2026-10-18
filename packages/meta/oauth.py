"""Instagram Login only. No Facebook Login host or Page token fallback."""
from urllib.parse import urlencode

import httpx

SCOPES = ('instagram_business_basic', 'instagram_business_manage_comments',
          'instagram_business_manage_messages')


class MetaOAuthError(Exception):
    pass


def authorization_url(settings, state):
    return 'https://www.instagram.com/oauth/authorize?' + urlencode({
        'client_id': settings.instagram_app_id,
        'redirect_uri': settings.redirect_uri,
        'response_type': 'code', 'scope': ','.join(SCOPES),
        'state': state, 'enable_fb_login': '0', 'force_authentication': '1'})


async def exchange_code(settings, code):
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20,connect=5), follow_redirects=False) as client:
            short = await client.post('https://api.instagram.com/oauth/access_token', data={
                'client_id': settings.instagram_app_id, 'client_secret': settings.instagram_app_secret,
                'grant_type': 'authorization_code', 'redirect_uri': settings.redirect_uri, 'code': code})
            if short.status_code != 200:
                raise MetaOAuthError()
            payload = short.json()
            token = payload['access_token']
            # GET token exchange mandated by provider; never log HTTP request URLs.
            long = await client.get('https://graph.instagram.com/access_token', params={
                'grant_type': 'ig_exchange_token', 'client_secret': settings.instagram_app_secret,
                'access_token': token})
            if long.status_code != 200:
                raise MetaOAuthError()
            credential = long.json()
            token = credential['access_token']
            expires = int(credential['expires_in'])
            profile = await client.get('https://graph.instagram.com/' + settings.meta_api_version + '/me',
                params={'fields': 'user_id,username'}, headers={'Authorization': 'Bearer ' + token})
            if profile.status_code != 200:
                raise MetaOAuthError()
            identity = profile.json()
            # user_id is explicit; never substitute an arbitrary id field silently.
            identity['user_id'] = str(identity['user_id'])
            permissions = payload.get('permissions', [])
            if isinstance(permissions,str):
                permissions = permissions.split(',')
            if (not identity['user_id'].isdigit() or not token or expires <= 0
                    or not set(SCOPES).issubset(set(permissions))):
                raise MetaOAuthError()
            return identity, token, permissions, expires
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        raise MetaOAuthError() from None


async def subscribe_comments(settings, ig_user_id, token):
    """Account subscription only; never calls /messages or sends a private reply."""
    if not str(ig_user_id).isdigit():
        raise MetaOAuthError()
    url = 'https://graph.instagram.com/' + settings.meta_api_version + '/' + str(ig_user_id) + '/subscribed_apps'
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20,connect=5),follow_redirects=False) as client:
            headers = {'Authorization':'Bearer ' + token}
            response = await client.post(url,headers=headers,data={'subscribed_fields':'comments'})
            if response.status_code != 200 or response.json().get('success') is not True:
                raise MetaOAuthError()
            check = await client.get(url,headers=headers)
            if check.status_code != 200:
                return 'accepted'
            items = check.json().get('data',[])
            if not isinstance(items,list):
                return 'accepted'
            for item in items:
                if (isinstance(item,dict) and str(item.get('id')) == settings.instagram_app_id
                        and 'comments' in item.get('subscribed_fields',[])):
                    return 'confirmed'
            return 'accepted'
    except (httpx.HTTPError,KeyError,ValueError,TypeError):
        raise MetaOAuthError() from None
