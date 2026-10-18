import html
from pathlib import Path
import re
import secrets
from urllib.parse import quote, urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get('/privacy', response_class=HTMLResponse)
async def privacy(request: Request):
    settings = request.app.state.settings
    name = settings.privacy_controller_name.strip()
    email = settings.privacy_contact_email.strip()
    url = settings.privacy_contact_url.strip()
    contact = None
    # Publish only explicitly configured, syntactically valid contact information.
    if re.fullmatch(r'[^\s@<>?&#]+@[^\s@<>?&#]+\.[^\s@<>?&#]+', email):
        contact = '<a href="mailto:' + html.escape(quote(email,safe='@.'),quote=True) + '">' + html.escape(email) + '</a>'
    elif url:
        parsed = urlsplit(url)
        if parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password:
            contact = '<a href="' + html.escape(url,quote=True) + '" rel="noreferrer">Canal de privacidade</a>'
    missing = not name or contact is None
    notice = ('<aside aria-label="Aviso de preenchimento"><strong>Aviso provisório:</strong> a identificação do responsável e/ou o canal de privacidade ainda não foram informados. Este texto precisa ser finalizado antes de ser usado como política definitiva na revisão ou operação pública.</aside>' if missing else '')
    deletion = ('<p>Solicite pelo contato indicado acima e informe a conta Instagram relacionada, o tipo de dado que deseja acessar, corrigir ou excluir e, se souber, o período aproximado. O atendimento previsto é manual, pelo responsável. Credenciais e dados vinculados à conta devem ser avaliados nesse procedimento.</p>' if contact else '<p><strong>O canal para pedidos de privacidade e exclusão ainda não foi publicado.</strong> Nesta fase, esta página não oferece um meio ativo para registrar sua solicitação. O responsável precisa definir e publicar um e-mail ou canal antes da operação pública. Quando disponível, solicite por esse contato, informando a conta Instagram, o tipo de dado e o período aproximado; não envie credenciais.</p>')
    nonce = secrets.token_urlsafe(24)
    text = Path(__file__).with_name('pages').joinpath('privacy.html').read_text()
    # Replace user-configured content last, so template tokens in a name remain text.
    text = text.replace('__NONCE__',nonce).replace('__NOTICE__',notice).replace('__DELETION__',deletion)
    text = text.replace('__CONTROLLER__',html.escape(name) if name else 'identificação pendente de fornecimento pelo operador')
    text = text.replace('__CONTACT__',contact or 'canal ainda não informado pelo operador')
    response = HTMLResponse(text)
    response.headers['Content-Security-Policy'] = "default-src 'none'; style-src 'nonce-"+nonce+"'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response
