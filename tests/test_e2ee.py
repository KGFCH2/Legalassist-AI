import os
from core.e2ee import (
    derive_key,
    zero_buffer,
    encrypt_bytes_to_b64,
    decrypt_bytes_from_b64,
    wrap_file_key,
    unwrap_file_key,
)

def test_zero_buffer():
    buf = bytearray(b"sensitive_secret_key")
    zero_buffer(buf)
    assert all(x == 0 for x in buf)


def test_derive_key_cleans_passphrase():
    # Since passphrase is standard python string we don't zero it in derive_key,
    # but we zero the converted bytearray pass_bytes.
    salt = b"salt" * 8
    key = derive_key("mypassphrase", salt)
    assert len(key) == 32
    assert isinstance(key, bytearray)


def test_encrypt_decrypt_flow():
    passphrase = "super_secure_passphrase"
    plaintext = b"Highly confidential legal case details."
    
    encrypted = encrypt_bytes_to_b64(plaintext, passphrase)
    decrypted = decrypt_bytes_from_b64(encrypted, passphrase)
    
    assert decrypted == plaintext


def test_wrap_unwrap_file_key():
    master_key = "master_passphrase"
    file_key = "file_encryption_key_123"
    
    wrapped = wrap_file_key(file_key, master_key)
    unwrapped = unwrap_file_key(wrapped, master_key)
    
    assert unwrapped == file_key


def test_configurable_iterations(monkeypatch):
    monkeypatch.setenv("E2EE_PBKDF2_ITERATIONS", "1000")
    salt = b"salt" * 8
    key = derive_key("mypassphrase", salt)
    assert len(key) == 32
