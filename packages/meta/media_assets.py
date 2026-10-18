"""Allow provider CDN image URLs only. Never accept arbitrary hosts or access tokens."""
from urllib.parse import urlsplit,parse_qs


def safe_image_url(value):
    if not isinstance(value,str) or len(value)>8192:return None
    try:
        u=urlsplit(value)
        host=(u.hostname or '').lower()
        if u.scheme!='https' or u.username or u.password or u.port not in (None,443):return None
        if not any(host.endswith('.'+domain) for domain in ('cdninstagram.com','fbcdn.net')):return None
        if any(k.lower() in ('access_token','client_secret','token') for k in parse_qs(u.query)):return None
        if any(c.isspace() for c in value):return None
        return value
    except ValueError:return None
