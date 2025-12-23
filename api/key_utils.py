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
