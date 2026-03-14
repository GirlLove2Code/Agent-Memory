"""
Vivioo Memory — Encryption (Step 1)
Handles encryption at rest for 🔴 Locked branches.

Uses Fernet symmetric encryption (from Python cryptography lib).
Passphrase → key derivation → encrypt/decrypt.

All local. Nothing leaves the machine.
"""

import os
import json
import base64
import hashlib
from typing import Optional

# Try to import cryptography — if not available, locked branches won't work
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

# Session unlock state — tracks which branches are unlocked this session
_unlocked_branches: dict = {}  # branch_path -> Fernet instance


def _derive_key(passphrase: str, salt: bytes = None) -> tuple:
    """
    Derive an encryption key from a passphrase.

    Args:
        passphrase: the user's passphrase
        salt: random salt (generated if not provided)

    Returns:
        (key_bytes, salt_bytes)
    """
    if not HAS_CRYPTO:
        raise RuntimeError(
            "cryptography library not installed. "
            "Run: pip install cryptography"
        )

    if salt is None:
        salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
    return key, salt


def encrypt_data(data: str, passphrase: str) -> dict:
    """
    Encrypt a string with a passphrase.

    Args:
        data: the text to encrypt
        passphrase: the passphrase

    Returns:
        {"encrypted": base64_string, "salt": base64_string}
    """
    key, salt = _derive_key(passphrase)
    f = Fernet(key)
    encrypted = f.encrypt(data.encode())
    return {
        "encrypted": base64.urlsafe_b64encode(encrypted).decode(),
        "salt": base64.urlsafe_b64encode(salt).decode(),
    }


def decrypt_data(encrypted_data: dict, passphrase: str) -> Optional[str]:
    """
    Decrypt data with a passphrase.

    Args:
        encrypted_data: {"encrypted": base64_string, "salt": base64_string}
        passphrase: the passphrase

    Returns:
        Decrypted string, or None if passphrase is wrong
    """
    try:
        salt = base64.urlsafe_b64decode(encrypted_data["salt"])
        key, _ = _derive_key(passphrase, salt)
        f = Fernet(key)
        encrypted = base64.urlsafe_b64decode(encrypted_data["encrypted"])
        return f.decrypt(encrypted).decode()
    except Exception:
        return None


def unlock_branch(branch_path: str, passphrase: str, branch_dir: str) -> bool:
    """
    Unlock a locked branch for this session.

    Args:
        branch_path: e.g. "about-builder/health"
        passphrase: the passphrase to try
        branch_dir: path to the branch directory on disk

    Returns:
        True if unlock succeeded, False if wrong passphrase
    """
    # Try to decrypt the branch's lock file
    lock_file = os.path.join(branch_dir, ".lock")
    if not os.path.exists(lock_file):
        return False

    with open(lock_file, "r") as f:
        lock_data = json.load(f)

    result = decrypt_data(lock_data, passphrase)
    if result is not None:
        # Store the Fernet instance for this session
        salt = base64.urlsafe_b64decode(lock_data["salt"])
        key, _ = _derive_key(passphrase, salt)
        _unlocked_branches[branch_path] = Fernet(key)
        return True
    return False


def is_unlocked(branch_path: str) -> bool:
    """Check if a branch is unlocked this session."""
    return branch_path in _unlocked_branches


def lock_branch(branch_path: str, passphrase: str, branch_dir: str) -> None:
    """
    Set up encryption for a branch. Creates the .lock file.

    Args:
        branch_path: e.g. "about-builder/health"
        passphrase: the passphrase to use
        branch_dir: path to the branch directory on disk
    """
    # Create a lock verification file
    lock_data = encrypt_data("vivioo-memory-locked", passphrase)
    lock_file = os.path.join(branch_dir, ".lock")
    with open(lock_file, "w") as f:
        json.dump(lock_data, f, indent=2)


def encrypt_entry(entry_data: str, branch_path: str, passphrase: str = None) -> dict:
    """
    Encrypt an entry's content for storage.

    Uses the session key if branch is unlocked, otherwise requires passphrase.
    """
    if branch_path in _unlocked_branches:
        f = _unlocked_branches[branch_path]
        encrypted = f.encrypt(entry_data.encode())
        return {"encrypted": base64.urlsafe_b64encode(encrypted).decode()}

    if passphrase is None:
        raise ValueError(f"Branch '{branch_path}' is locked and no passphrase provided")

    return encrypt_data(entry_data, passphrase)


def decrypt_entry(encrypted_entry: dict, branch_path: str,
                  passphrase: str = None) -> Optional[str]:
    """
    Decrypt an entry's content.

    Uses the session key if branch is unlocked, otherwise requires passphrase.
    """
    if branch_path in _unlocked_branches:
        f = _unlocked_branches[branch_path]
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_entry["encrypted"])
            return f.decrypt(encrypted).decode()
        except Exception:
            return None

    if passphrase is None:
        return None

    return decrypt_data(encrypted_entry, passphrase)


def clear_session():
    """Clear all unlocked branches — call at session end."""
    _unlocked_branches.clear()
