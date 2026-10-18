from dataclasses import replace
import json
import httpx
import pytest

from packages.meta.private_reply import send_once,validate_text
from tests.test_auth_oauth import config


def test_message_limit_is_utf8_bytes():
    validate_text('á'*500,1000,'bytes')
    with pytest.raises(ValueError):validate_text('á'*501,1000,'bytes')
    with pytest.raises(ValueError):validate_text('ok',1000,'codepoints')
    with pytest.raises(ValueError):validate_text('ok',1001,'bytes')


@pytest.mark.parametrize('kind,expected',[
    ('success','accepted'),('timeout','unknown'),('server_error','unknown'),
    ('missing_id','unknown'),('wrong_recipient','unknown'),('permanent_error','failed')])
def test_one_transport_invocation_only_and_uncertainty_blocks_retry(config,kind,expected):
    settings=replace(config,meta_max_message_length=1000,meta_message_length_unit='bytes')
    calls=[]
    def handler(request):
        calls.append(request)
        assert request.url.path.endswith('/123/messages')
        assert json.loads(request.content)=={'recipient':{'comment_id':'456'},'message':{'text':'Teste'}}
        if kind=='timeout':raise httpx.ReadTimeout('uncertain',request=request)
        if kind=='server_error':return httpx.Response(503,json={'error':{}})
        if kind=='missing_id':return httpx.Response(200,json={})
        if kind=='permanent_error':return httpx.Response(400,json={'error':{'code':190,'message':'sensitive-do-not-store'}})
        return httpx.Response(200,json={'message_id':'message-test','recipient_id':'789' if kind=='success' else '000'})
    factory=lambda:httpx.Client(transport=httpx.MockTransport(handler),follow_redirects=False)
    result=send_once(settings,'123','456','789','private-token','Teste',factory)
    assert result['status']==expected
    assert len(calls)==1
    assert 'private-token' not in json.dumps(result)
    assert 'sensitive-do-not-store' not in json.dumps(result)


def test_provider_timestamp_supports_actual_meta_offset_and_rejects_naive():
    from packages.domain.timestamps import provider_timestamp
    assert provider_timestamp('2026-10-17T04:41:45+0000')==provider_timestamp('2026-10-17T04:41:45Z')
    with pytest.raises(ValueError):provider_timestamp('2026-10-17T04:41:45')
