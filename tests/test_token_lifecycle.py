import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from packages.meta.token_lifecycle import TokenLifecycleError, checked_payload, refresh_eligibility, refresh_token

NOW = datetime.now(timezone.utc)


def snapshot():
    return dict(refreshed_at=NOW-timedelta(days=2), expires_at=NOW+timedelta(days=5),
                scopes=['instagram_business_basic'], token='old-test-token', ig_user_id='111')


def test_refresh_age_expiry_permission_boundaries():
    s = snapshot()
    for age, lifetime, scopes, expected in [
        (23, 1, s['scopes'], 'too_young'), (24, 1, s['scopes'], 'eligible'),
        (48, 0, s['scopes'], 'expired'), (48, 1, [], 'missing_permission')]:
        assert refresh_eligibility(NOW-timedelta(hours=age), NOW+timedelta(days=lifetime), NOW, scopes) == expected


@pytest.mark.parametrize('status,body,reason', [
    (400, {'error': {'code': 190, 'message': 'secret'}}, 'reconnect_required'),
    (403, {}, 'permission_denied'), (503, {}, 'provider_unavailable'),
    (200, [], 'invalid_response')])
def test_safe_failure_classification(status, body, reason):
    with pytest.raises(TokenLifecycleError) as exc:
        checked_payload(httpx.Response(status, json=body))
    assert str(exc.value) == reason and 'secret' not in str(exc.value)


@pytest.mark.parametrize('identity,expected', [('111', None), ('222', 'identity_mismatch')])
def test_refresh_verifies_identity_without_messages(identity, expected):
    calls = []
    def handler(request):
        calls.append(request)
        assert request.method == 'GET' and '/messages' not in request.url.path
        if request.url.path == '/refresh_access_token':
            assert request.url.params['grant_type'] == 'ig_refresh_token'
            return httpx.Response(200, json={'access_token':'new-test-token','expires_in':5184000})
        return httpx.Response(200, json={'user_id':identity})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
            return await refresh_token(SimpleNamespace(meta_api_version='v26.0'), snapshot(), NOW, client)
    if expected:
        with pytest.raises(TokenLifecycleError, match=expected):
            asyncio.run(run())
    else:
        assert asyncio.run(run()) == ('new-test-token',5184000)
    assert len(calls) == 2


def test_young_token_does_not_call_provider():
    s = snapshot()
    s['refreshed_at'] = NOW
    def handler(request):
        pytest.fail('Premature external refresh')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await refresh_token(SimpleNamespace(meta_api_version='v26.0'), s, NOW, client)
    with pytest.raises(TokenLifecycleError, match='too_young'):
        asyncio.run(run())


def test_refresh_timeout_is_not_retried():
    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout('sensitive URL must not escape', request=request)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await refresh_token(SimpleNamespace(meta_api_version='v26.0'), snapshot(), NOW, client)
    with pytest.raises(TokenLifecycleError, match='transport_uncertain'):
        asyncio.run(run())
    assert len(calls) == 1
