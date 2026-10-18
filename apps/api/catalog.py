"""Private catalog and immutable campaign snapshots. No dispatch path."""
import json
from uuid import uuid4
from psycopg.types.json import Jsonb
from apps.api.accounts import AccountStore
from packages.meta.media_assets import safe_image_url
from packages.domain.campaigns import clean_keywords,clean_links,render_message


class ConflictError(Exception):pass


class PublicationInUse(ConflictError):pass


class CatalogStore(AccountStore):
    def account(self,c,user,org,account):
        self.require_operator(c,user,org)
        row=c.execute('SELECT * FROM instagram_link.instagram_accounts WHERE id=%s AND organization_id=%s',(account,org)).fetchone()
        if not row:raise PermissionError()
        return row

    def audit(self,c,user,org,action,target,version=None):
        c.execute('INSERT INTO instagram_link.catalog_audit(organization_id,actor_id,action,target_id,version) VALUES (%s,%s,%s,%s,%s)',(org,user,action,target,version))

    def products(self,user,org):
        with self.connect() as c:
            self.require_operator(c,user,org)
            return c.execute('SELECT * FROM instagram_link.products WHERE organization_id=%s ORDER BY created_at DESC',(org,)).fetchall()

    def save_product(self,user,org,data,product_id=None):
        if not data['name'].strip():raise ValueError('Informe o nome do produto')
        links=clean_links(data['links'])
        with self.connect() as c:
            self.require_operator(c,user,org)
            if product_id:
                old=c.execute('SELECT * FROM instagram_link.products WHERE id=%s AND organization_id=%s FOR UPDATE',(product_id,org)).fetchone()
                if not old:raise PermissionError()
                if old['version']!=data['expected_version']:raise ConflictError()
                row=c.execute('UPDATE instagram_link.products SET name=%s,description=%s,links=%s,active=%s,version=version+1,updated_at=now() WHERE id=%s RETURNING *',(data['name'].strip(),data['description'],Jsonb(links),data['active'],product_id)).fetchone()
            else:
                row=c.execute('INSERT INTO instagram_link.products(organization_id,name,description,links,active) VALUES (%s,%s,%s,%s,%s) RETURNING *',(org,data['name'].strip(),data['description'],Jsonb(links),data['active'])).fetchone()
            self.audit(c,user,org,'product_saved',row['id'],row['version'])
            return row

    def archive_product(self,user,org,pid,version):
        with self.connect() as c:
            self.require_operator(c,user,org)
            old=c.execute('SELECT * FROM instagram_link.products WHERE id=%s AND organization_id=%s FOR UPDATE',(pid,org)).fetchone()
            if not old:raise PermissionError()
            if old['version']!=version:raise ConflictError()
            row=c.execute('UPDATE instagram_link.products SET active=false,version=version+1,updated_at=now() WHERE id=%s RETURNING *',(pid,)).fetchone()
            self.audit(c,user,org,'product_archived',pid,row['version'])
            return row

    def publications(self,user,org,account):
        with self.connect() as c:
            self.account(c,user,org,account)
            return c.execute('SELECT * FROM instagram_link.publications WHERE account_id=%s AND organization_id=%s ORDER BY published_at DESC',(account,org)).fetchall()

    def save_publications(self,user,org,account,items,*,sync_state=None,next_after=None):
        with self.connect() as c:
            self.account(c,user,org,account)
            if sync_state is not None:
                current=c.execute('SELECT publications_synced_at FROM instagram_link.instagram_accounts WHERE id=%s AND organization_id=%s FOR UPDATE',(account,org)).fetchone()
                if current['publications_synced_at']!=sync_state['synced_at']:raise ConflictError()
            for item in items:
                c.execute('INSERT INTO instagram_link.publications(organization_id,account_id,ig_media_id,caption,permalink,media_type,published_at,thumbnail_url,media_url,media_product_type) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(account_id,ig_media_id) DO UPDATE SET caption=EXCLUDED.caption,permalink=EXCLUDED.permalink,media_type=EXCLUDED.media_type,thumbnail_url=EXCLUDED.thumbnail_url,media_url=EXCLUDED.media_url,media_product_type=EXCLUDED.media_product_type,synced_at=now()', (org,account,item['id'],item.get('caption','')[:3000],item['permalink'],item['media_type'],item['timestamp'],safe_image_url(item.get('thumbnail_url')),safe_image_url(item.get('media_url')),item.get('media_product_type')))
            if sync_state is not None:
                encrypted=self.cipher.encrypt(next_after.encode()) if next_after else None
                c.execute('UPDATE instagram_link.instagram_accounts SET publications_cursor=%s,publications_synced_at=now() WHERE id=%s AND organization_id=%s',(encrypted,account,org))
            self.audit(c,user,org,'publications_synced',account)

    def campaigns(self,user,org,account):
        with self.connect() as c:
            self.account(c,user,org,account)
            return c.execute('SELECT c.*,v.rules,v.template,v.rendered_message,v.product_snapshot,p.permalink,p.caption,p.published_at,p.media_type,p.thumbnail_url,p.media_url,p.media_product_type FROM instagram_link.campaigns c JOIN instagram_link.campaign_versions v ON v.campaign_id=c.id AND v.version=c.version JOIN instagram_link.publications p ON p.id=c.publication_id WHERE c.account_id=%s AND c.organization_id=%s ORDER BY c.created_at DESC',(account,org)).fetchall()

    def campaign(self,user,org,account,campaign_id):
        items=self.campaigns(user,org,account)
        row=next((r for r in items if r['id']==campaign_id),None)
        if not row:raise PermissionError()
        return row

    def save_campaign(self,user,org,account,data,campaign_id=None):
        if not data['name'].strip():raise ValueError('Informe o nome da campanha')
        rules={'include':clean_keywords(data['include'],True),'exclude':clean_keywords(data['exclude']),'ignore_accents':data['ignore_accents']}
        with self.connect() as c:
            connection=self.account(c,user,org,account)
            if not campaign_id and connection['connection_status']!='connected':raise ValueError('Conecte a conta Instagram antes de criar uma automação')
            product=c.execute('SELECT * FROM instagram_link.products WHERE id=%s AND organization_id=%s FOR SHARE',(data['product_id'],org)).fetchone()
            publication=c.execute('SELECT id FROM instagram_link.publications WHERE id=%s AND organization_id=%s AND account_id=%s FOR UPDATE',(data['publication_id'],org,account)).fetchone()
            if not product or not publication:raise PermissionError()
            if not campaign_id and c.execute("SELECT id FROM instagram_link.campaigns WHERE publication_id=%s AND organization_id=%s AND account_id=%s AND state<>'archived'",(data['publication_id'],org,account)).fetchone():
                raise PublicationInUse()
            if not product['active']:raise ValueError('Produto inativo')
            snapshot={'id':str(product['id']),'version':product['version'],'name':product['name'],'links':product['links']}
            rendered=render_message(data['template'],snapshot,self.settings)
            if campaign_id:
                old=c.execute('SELECT * FROM instagram_link.campaigns WHERE id=%s AND organization_id=%s AND account_id=%s FOR UPDATE',(campaign_id,org,account)).fetchone()
                if not old:raise PermissionError()
                if old['publication_id']!=data['publication_id']:raise ValueError('A publicação de uma automação existente não pode ser substituída')
                if old['state']=='archived':raise ValueError('Campanha arquivada não pode ser alterada')
                if old['version']!=data['expected_version']:raise ConflictError()
                row=c.execute("UPDATE instagram_link.campaigns SET name=%s,product_id=%s,publication_id=%s,version=version+1,state='draft',updated_at=now() WHERE id=%s RETURNING *",(data['name'].strip(),product['id'],publication['id'],campaign_id)).fetchone()
            else:
                row=c.execute('INSERT INTO instagram_link.campaigns(organization_id,account_id,publication_id,product_id,name) VALUES (%s,%s,%s,%s,%s) RETURNING *',(org,account,publication['id'],product['id'],data['name'].strip())).fetchone()
            c.execute('INSERT INTO instagram_link.campaign_versions(campaign_id,version,rules,product_snapshot,template,rendered_message,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s)',(row['id'],row['version'],Jsonb(rules),Jsonb(snapshot),data['template'],rendered,user))
            self.audit(c,user,org,'campaign_version_saved',row['id'],row['version'])
            return {**row,'rules':rules,'product_snapshot':snapshot,'template':data['template'],'rendered_message':rendered}

    def archive_campaign(self,user,org,account,cid,version):
        with self.connect() as c:
            self.require_admin(c,user,org)
            self.account(c,user,org,account)
            old=c.execute('SELECT * FROM instagram_link.campaigns WHERE id=%s AND organization_id=%s AND account_id=%s FOR UPDATE',(cid,org,account)).fetchone()
            if not old:raise PermissionError()
            if old['version']!=version:raise ConflictError()
            c.execute("UPDATE instagram_link.campaigns SET state='archived',updated_at=now() WHERE id=%s",(cid,))
            self.audit(c,user,org,'campaign_archived',cid,version)
            return {'archived':True}

    def prior_attempts(self,account):
        with self.connect() as c:
            return {r['comment_id'] for r in c.execute('SELECT comment_id FROM instagram_link.m0_private_reply_attempts WHERE account_id=%s AND attempt_count>0',(account,)).fetchall()}

    def save_review(self,user,org,account,cid,version,review):
        with self.connect() as c:
            self.account(c,user,org,account)
            row=c.execute('SELECT version,state,product_id FROM instagram_link.campaigns WHERE id=%s AND organization_id=%s AND account_id=%s FOR UPDATE',(cid,org,account)).fetchone()
            if not row:raise PermissionError()
            if row['version']!=version or row['state']=='archived':raise ConflictError()
            p=c.execute('SELECT active FROM instagram_link.products WHERE id=%s FOR SHARE',(row['product_id'],)).fetchone()
            if not p['active']:raise ValueError('Produto inativo')
            result=c.execute('INSERT INTO instagram_link.pilot_reviews(organization_id,campaign_id,campaign_version,encrypted_review,reviewed_by) VALUES (%s,%s,%s,%s,%s) RETURNING id,created_at,expires_at',(org,cid,version,self.cipher.encrypt(json.dumps(review).encode()),user)).fetchone()
            c.execute("UPDATE instagram_link.campaigns SET state='paused',updated_at=now() WHERE id=%s",(cid,))
            self.audit(c,user,org,'pilot_review_prepared',cid,version)
            return result

    def reviews(self,user,org,account):
        with self.connect() as c:
            self.account(c,user,org,account)
            return c.execute('SELECT r.id,r.campaign_id,r.campaign_version,r.created_at,r.expires_at,c.name FROM instagram_link.pilot_reviews r JOIN instagram_link.campaigns c ON c.id=r.campaign_id WHERE r.organization_id=%s AND c.account_id=%s ORDER BY r.created_at DESC LIMIT 50',(org,account)).fetchall()

    def audit_history(self,user,org,account):
        with self.connect() as c:
            self.account(c,user,org,account)
            return c.execute("SELECT a.action,a.version,a.created_at,c.name FROM instagram_link.catalog_audit a JOIN instagram_link.campaigns c ON c.id=a.target_id WHERE a.organization_id=%s AND c.account_id=%s ORDER BY a.created_at DESC LIMIT 50",(org,account)).fetchall()

    def versions(self,user,org,account,cid):
        self.campaign(user,org,account,cid)
        with self.connect() as c:
            self.require_operator(c,user,org)
            return c.execute('SELECT version,rules,product_snapshot,template,rendered_message,created_at FROM instagram_link.campaign_versions WHERE campaign_id=%s ORDER BY version DESC',(cid,)).fetchall()

    def review_detail(self,user,org,account,rid):
        from datetime import datetime,timezone
        with self.connect() as c:
            self.account(c,user,org,account)
            row=c.execute('SELECT r.*,c.version AS current_version,c.state AS campaign_state,c.name FROM instagram_link.pilot_reviews r JOIN instagram_link.campaigns c ON c.id=r.campaign_id WHERE r.id=%s AND r.organization_id=%s AND c.account_id=%s',(rid,org,account)).fetchone()
            if not row:raise PermissionError()
            result=json.loads(self.cipher.decrypt(bytes(row['encrypted_review'])))
            return {**result,'review_id':str(row['id']),'expires_at':row['expires_at'],
                    'expired':row['expires_at']<=datetime.now(timezone.utc),
                    'stale':row['campaign_version']!=row['current_version'] or row['campaign_state']=='archived','name':row['name']}

    def pause_campaign(self,user,org,account,cid,version):
        with self.connect() as c:
            self.account(c,user,org,account)
            row=c.execute('SELECT version,state FROM instagram_link.campaigns WHERE id=%s AND organization_id=%s AND account_id=%s FOR UPDATE',(cid,org,account)).fetchone()
            if not row:raise PermissionError()
            if row['version']!=version:raise ConflictError()
            if row['state']=='archived':raise ValueError('Campanha arquivada não pode ser alterada')
            c.execute("UPDATE instagram_link.campaigns SET state='paused',updated_at=now() WHERE id=%s",(cid,))
            self.audit(c,user,org,'campaign_paused',cid,version)
            return {'paused':True}

    def sync_state(self,user,org,account):
        with self.connect() as c:
            row=self.account(c,user,org,account)
            value=row['publications_cursor']
            return {'after':self.cipher.decrypt(bytes(value)).decode() if value else None,'synced_at':row['publications_synced_at']}

    def publications_page(self,user,org,account,cursor=None,limit=12):
        from cryptography.fernet import InvalidToken
        from uuid import UUID
        from datetime import datetime
        if not 1<=limit<=25:raise ValueError('Invalid page size')
        with self.connect() as c:
            connection=self.account(c,user,org,account)
            params=[account,org];condition=''
            if cursor:
                try:
                    value=json.loads(self.cipher.decrypt(cursor.encode(),ttl=86400))
                    if value['org']!=str(org) or value['account']!=str(account):raise ValueError()
                    position=datetime.fromisoformat(value['date']);pid=UUID(value['id'])
                except (ValueError,KeyError,TypeError,InvalidToken):raise ValueError('Página expirada ou inválida. Atualize a lista.') from None
                condition=' AND (p.published_at,p.id)<(%s,%s)';params.extend([position,pid])
            rows=c.execute("SELECT p.*,COALESCE((SELECT jsonb_agg(jsonb_build_object('id',c.id,'name',c.name,'state',c.state,'version',c.version) ORDER BY c.created_at DESC) FROM instagram_link.campaigns c WHERE c.publication_id=p.id AND c.organization_id=p.organization_id AND c.account_id=p.account_id),'[]'::jsonb) AS automations FROM instagram_link.publications p WHERE p.account_id=%s AND p.organization_id=%s"+condition+' ORDER BY p.published_at DESC,p.id DESC LIMIT %s',(*params,limit+1)).fetchall()
            more=len(rows)>limit;rows=rows[:limit]
            end=None
            if rows:
                last=rows[-1]
                end=self.cipher.encrypt(json.dumps({'org':str(org),'account':str(account),'date':last['published_at'].isoformat(),'id':str(last['id'])}).encode()).decode()
            return {'items':rows,'next_cursor':end if more else None,'end_cursor':end,'has_more_remote':bool(connection['publications_cursor']),'synced_at':connection['publications_synced_at']}
