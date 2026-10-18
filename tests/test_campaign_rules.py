from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
import pytest
from packages.domain.campaigns import match_rules,render_message,clean_links,assess_comment

RULES={'include':['QUERO O LINK','LINK'],'exclude':['não quero'],'ignore_accents':False}

@pytest.mark.parametrize('text,expected',[('Quero o LINK!',True),('linkado',False),('não quero LINK',False),('não_quero link',False),('Quero outro o link',True),('ＬＩＮＫ',True),('',False)])
def test_whole_words_and_exclusions(text,expected):assert match_rules(text,RULES)[0]==expected


def test_phrase_and_accents():
    rules={'include':['café especial'],'exclude':[],'ignore_accents':False}
    assert not match_rules('cafe especial',rules)[0]
    assert not match_rules('café muito especial',rules)[0]
    assert match_rules('cafe especial',{**rules,'ignore_accents':True})[0]


@pytest.mark.parametrize('url',['http://example.com','javascript:alert(1)','https://user:pass@example.com','https://127.0.0.1','https://localhost','https://example.com/a b'])
def test_insecure_links_denied(url):
    with pytest.raises(ValueError):clean_links([{'label':'Produto','url':url}])


def test_message_is_snapshot_with_links_and_utf8_limit():
    settings=SimpleNamespace(meta_max_message_length=1000,meta_message_length_unit='bytes')
    product={'name':'Café','links':[{'label':'Comprar','url':'https://example.com/produto'}]}
    assert render_message('{{product_name}}\n{{product_links}}',product,settings)=='Café\nComprar: https://example.com/produto'
    for template in ('sem links','{{unexpected}} {{product_links}}','á'*500+'{{product_links}}'):
        with pytest.raises(ValueError):render_message(template,product,settings)


def test_review_excludes_historical_own_duplicate_nested_unknown_and_frequency():
    now=datetime.now(timezone.utc)
    base={'id':'1','from':{'id':'22'},'timestamp':now.isoformat(),'text':'LINK','hidden':False}
    cutoff=now-timedelta(minutes=5)
    def check(row,used=set(),seen=None):return assess_comment(row,RULES,now,cutoff,'11',used,set() if seen is None else seen)['reason']
    assert check(base)=='eligible_for_review'
    assert check({**base,'hidden':None})=='visibility_unconfirmed'
    assert check({**base,'parent_id':'9'})=='unsupported_nested'
    assert check({**base,'from':{'id':'11'}})=='own_comment'
    assert check({**base,'timestamp':(now-timedelta(days=1)).isoformat()})=='before_campaign'
    assert check(base,{'1'})=='already_attempted'
    seen=set();assert check(base,seen=seen)=='eligible_for_review'
    assert check({**base,'id':'2'},seen=seen)=='frequency_limit'
