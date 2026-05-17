import hashlib
import secrets
import json
from datetime import datetime


def hash_key(plain: str) -> str:
    return hashlib.sha256(plain.encode('utf-8')).hexdigest()


def mask_key(plain: str) -> str:
    if not plain or len(plain) <= 12:
        return plain
    return plain[:8] + '...' + plain[-4:]


def generate_secret_key() -> str:
    return 'sk-' + secrets.token_urlsafe(32)


def parse_json_field(val):
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    try:
        return json.loads(val)
    except Exception:
        return {}


def now_iso():
    return datetime.utcnow().isoformat()


def get_fernet_key() -> bytes:
    import os
    import base64
    secret = os.environ.get('API_KEY_ENCRYPTION_SECRET')
    if not secret:
        secret = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SECRET_KEY') or 'default-manhattan-fallback-secret-key-12345'
    hasher = hashlib.sha256(secret.encode('utf-8'))
    return base64.urlsafe_b64encode(hasher.digest())


def encrypt_api_key(plain_key: str) -> str:
    if not plain_key:
        return ''
    from cryptography.fernet import Fernet
    key = get_fernet_key()
    f = Fernet(key)
    return f.encrypt(plain_key.encode('utf-8')).decode('utf-8')


def decrypt_api_key(encrypted_key: str) -> str:
    if not encrypted_key:
        return ''
    from cryptography.fernet import Fernet
    key = get_fernet_key()
    f = Fernet(key)
    return f.decrypt(encrypted_key.encode('utf-8')).decode('utf-8')

