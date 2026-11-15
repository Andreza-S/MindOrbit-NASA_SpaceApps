"""Empacotamento do link (RNF04): criptografia e checksum. Pacote alterado é rejeitado."""
import pytest

from comms import package


def test_ida_e_volta_sem_perder_nada(tmp_path, monkeypatch):
    monkeypatch.setattr(package, "KEY_PATH", tmp_path / "k.key")
    payload, checksum = package.pack({"kind": "report", "risk": 42})
    assert package.unpack(payload, checksum) == {"kind": "report", "risk": 42}
    assert b"report" not in payload                         # não vai em claro


def test_pacote_alterado_e_rejeitado(tmp_path, monkeypatch):
    monkeypatch.setattr(package, "KEY_PATH", tmp_path / "k.key")
    payload, checksum = package.pack({"kind": "report"})
    altered = bytearray(payload); altered[len(altered) // 2] ^= 1
    with pytest.raises(ValueError):
        package.unpack(bytes(altered), checksum)
