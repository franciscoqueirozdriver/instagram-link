"""Single HTTP invocation, no retry and no redirect. Unknown always blocks resend."""
import httpx


def validate_text(text, limit, unit):
    if unit != 'bytes' or not 1 <= limit <= 1000:
        raise ValueError('Validated UTF-8 byte limit required')
    if not isinstance(text,str) or not text.strip() or len(text.encode('utf-8')) > limit:
        raise ValueError('Invalid message text or byte length')


def send_once(settings, ig_user_id, comment_id, expected_recipient, token, text, client_factory=None):
    validate_text(text,settings.meta_max_message_length,settings.meta_message_length_unit)
    if not str(ig_user_id).isdigit() or not str(comment_id).isdigit():
        raise ValueError('Numeric provider IDs required')
    factory = client_factory or (lambda: httpx.Client(
        timeout=httpx.Timeout(20,connect=5),follow_redirects=False,
        transport=httpx.HTTPTransport(retries=0)))
    try:
        with factory() as client:
            response=client.post(
                'https://graph.instagram.com/'+settings.meta_api_version+'/'+str(ig_user_id)+'/messages',
                headers={'Authorization':'Bearer '+token},
                json={'recipient':{'comment_id':str(comment_id)},'message':{'text':text}})
    except httpx.HTTPError:
        return {'status':'unknown','result_reason':'transport_outcome_uncertain'}
    result={'http_status':response.status_code}
    try:
        body=response.json()
        if not isinstance(body,dict):body={}
    except ValueError:
        body={}
    mid=body.get('message_id');rid=body.get('recipient_id')
    if isinstance(mid,str) and mid:
        result['provider_message_id']=mid
    if isinstance(rid,(str,int)):
        result['provider_recipient_id']=str(rid)
    if response.status_code==200 and result.get('provider_message_id'):
        if str(rid)!=str(expected_recipient):
            result.update(status='unknown',result_reason='recipient_not_confirmed')
        else:
            result.update(status='accepted',result_reason='meta_accepted')
    elif 400<=response.status_code<500:
        error=body.get('error',{})
        code=error.get('code') if isinstance(error,dict) else None
        if isinstance(code,int):result['provider_error_code']=str(code)
        result.update(status='failed',result_reason='explicit_rejection_no_retry')
    else:
        result.update(status='unknown',result_reason='provider_outcome_uncertain')
    return result
