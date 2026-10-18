"""Pure review rules. No sending, fetching URLs or template code execution."""
import ipaddress
import re
import unicodedata
from datetime import timedelta
from urllib.parse import urlsplit
from packages.domain.timestamps import provider_timestamp
from packages.meta.private_reply import validate_text


def tokens(text, ignore_accents=False):
    value=unicodedata.normalize('NFKC',text).casefold()
    if ignore_accents:value=''.join(c for c in unicodedata.normalize('NFD',value) if not unicodedata.combining(c))
    return re.findall(r'[^\W_]+',value,flags=re.UNICODE)


def match_phrase(text,phrase,ignore_accents=False):
    source,needle=tokens(text,ignore_accents),tokens(phrase,ignore_accents)
    return bool(needle) and any(source[i:i+len(needle)]==needle for i in range(len(source)-len(needle)+1))


def match_rules(text,rules):
    accent=rules.get('ignore_accents',False)
    if any(match_phrase(text,k,accent) for k in rules['exclude']):return False,'excluded_keyword'
    if any(match_phrase(text,k,accent) for k in rules['include']):return True,'matched'
    return False,'missing_keyword'


def clean_keywords(values, required=False):
    if not isinstance(values,list) or len(values)>30:raise ValueError('Use até 30 palavras ou frases por lista')
    result=[]
    for item in values:
        if not isinstance(item,str) or not 1<=len(item.strip())<=100 or not tokens(item):raise ValueError('Palavra-chave inválida')
        if item.strip() not in result:result.append(item.strip())
    if required and not result:raise ValueError('Inclua ao menos uma palavra-chave')
    return result


def clean_links(links):
    if not isinstance(links,list) or not 1<=len(links)<=5:raise ValueError('Cadastre entre 1 e 5 links')
    result=[]
    for link in links:
        label,url=link.get('label','').strip(),link.get('url','').strip()
        parts=urlsplit(url)
        if (not 1<=len(label)<=80 or not url or len(url)>2048 or parts.scheme!='https' or not parts.hostname
            or parts.username or parts.password or any(c.isspace() for c in url) or parts.hostname=='localhost'):
            raise ValueError('Links devem ser URLs HTTPS públicas, com rótulo e sem credenciais')
        try:
            address=ipaddress.ip_address(parts.hostname)
            if not address.is_global:raise ValueError('Link local não permitido')
        except ValueError as error:
            if 'Link local' in str(error):raise
            if '.' not in parts.hostname:raise ValueError('Domínio inválido') from None
        result.append({'label':label,'url':url})
    return result


def render_message(template,product,settings):
    if '{{product_links}}' not in template:raise ValueError('A mensagem deve conter {{product_links}}')
    fields=re.findall(r'{{\s*([^{}]+)\s*}}',template)
    if any(field not in ('product_name','product_links') for field in fields):raise ValueError('Variável de mensagem não permitida')
    message=template.replace('{{product_name}}',product['name']).replace('{{product_links}}','\n'.join(link['label']+': '+link['url'] for link in product['links']))
    if '{{' in message or '}}' in message:raise ValueError('Variável de mensagem inválida')
    validate_text(message,settings.meta_max_message_length,settings.meta_message_length_unit)
    return message


def assess_comment(comment,rules,now,cutoff,own_id,used_ids,seen_authors):
    cid=str(comment.get('id',''));author=comment.get('from',{}) or {};aid=str(author.get('id',''))
    reason=None
    try:created=provider_timestamp(comment.get('timestamp'))
    except ValueError:created=None
    if not cid or not aid:reason='missing_identity'
    elif comment.get('parent_id'):reason='unsupported_nested'
    elif comment.get('hidden') is True:reason='hidden_comment'
    elif comment.get('hidden') is not False:reason='visibility_unconfirmed'
    elif aid==own_id:reason='own_comment'
    elif created is None or created>now+timedelta(seconds=60):reason='untrusted_timestamp'
    elif created<cutoff:reason='before_campaign'
    elif created<=now-timedelta(days=7)+timedelta(minutes=5):reason='expired_window'
    elif cid in used_ids:reason='already_attempted'
    elif aid in seen_authors:reason='frequency_limit'
    else:
        matched,reason=match_rules(comment.get('text',''),rules)
        if matched:seen_authors.add(aid);reason='eligible_for_review'
    return {'comment_id':cid,'author_id':aid,'username':author.get('username',''),
        'text':comment.get('text','')[:500],'created_at':created.isoformat() if created else None,
        'eligible':reason=='eligible_for_review','reason':reason}
