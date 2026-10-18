from types import SimpleNamespace
import httpx
from packages.meta.catalog_read import read_collection


def test_cursor_pages_never_follow_provider_next_url(monkeypatch):
    called=[]
    def get(self,url,params,headers):
        called.append((url,dict(params)))
        page=len(called)
        return httpx.Response(200,json={'data':[{'id':str(page)}],'paging':{'next':'https://untrusted.invalid/steal','cursors':{'after':'cursor-'+str(page)}}})
    monkeypatch.setattr(httpx.Client,'get',get)
    rows,partial=read_collection(SimpleNamespace(meta_api_version='v26.0'),'synthetic-token','111/media','id')
    assert len(rows)==3 and partial
    assert all(url=='https://graph.instagram.com/v26.0/111/media' for url,_ in called)
    assert 'after' not in called[0][1] and called[1][1]['after']=='cursor-1'


def test_media_page_fields_cursor_and_safe_images(monkeypatch):
    from packages.meta.catalog_read import media_page
    from packages.meta.media_assets import safe_image_url
    called=[]
    def get(self,url,params,headers):
        called.append((url,params,headers))
        return httpx.Response(200,json={'data':[{'id':'9','media_type':'VIDEO','thumbnail_url':'https://scontent.cdninstagram.com/image.jpg'}],'paging':{'next':'https://malicious.invalid/?access_token=secret','cursors':{'after':'older'}}})
    monkeypatch.setattr(httpx.Client,'get',get)
    rows,cursor=media_page(SimpleNamespace(meta_api_version='v26.0'),{'token':'synthetic-token','ig_user_id':'111'},'start')
    assert cursor=='older' and len(rows)==1
    assert called[0][0]=='https://graph.instagram.com/v26.0/111/media'
    assert called[0][1]['after']=='start' and 'thumbnail_url' in called[0][1]['fields']
    assert called[0][2]['Authorization']=='Bearer synthetic-token'
    for value in ['http://scontent.cdninstagram.com/a','https://cdninstagram.com.evil.invalid/a','https://127.0.0.1/a','https://scontent.cdninstagram.com/a?access_token=secret']:
        assert safe_image_url(value) is None
    assert safe_image_url('https://scontent.cdninstagram.com/a.jpg')
