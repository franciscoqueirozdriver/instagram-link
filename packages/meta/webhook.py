"""Autenticação do envelope; normalização aguarda fixture real homologada."""
import hashlib
import hmac
import re


def valid_signature(body: bytes, signature: str, secret: str) -> bool:
    if not re.fullmatch(r'sha256=[a-fA-F0-9]{64}', signature):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature[7:].lower())
