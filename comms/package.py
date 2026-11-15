"""Empacotamento seguro (RF14, RNF04): JSON → zlib → Fernet, com checksum SHA-256."""
import hashlib
import json
import zlib

from cryptography.fernet import Fernet, InvalidToken

import config

KEY_PATH = config.DATA_DIR / "link.key"


def _key() -> bytes:
    """No protótipo, a chave fica num arquivo local compartilhado pela nave e pelo psicólogo de voo."""
    if not KEY_PATH.exists():
        KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        KEY_PATH.write_bytes(Fernet.generate_key())
    return KEY_PATH.read_bytes()


def pack(obj: dict) -> tuple[bytes, str]:
    token = Fernet(_key()).encrypt(zlib.compress(json.dumps(obj, ensure_ascii=False).encode("utf-8")))
    return token, hashlib.sha256(token).hexdigest()


def unpack(payload: bytes, checksum: str) -> dict:
    if hashlib.sha256(payload).hexdigest() != checksum:
        raise ValueError("Checksum SHA-256 não confere: o pacote foi alterado no caminho e foi rejeitado.")
    try:
        return json.loads(zlib.decompress(Fernet(_key()).decrypt(payload)))
    except InvalidToken:
        raise ValueError("A criptografia não confere: pacote rejeitado.")
