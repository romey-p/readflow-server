import hashlib
import secrets
from datetime import datetime
from typing import Optional

from app.core.db import get_db

def normalize_email(email: str) -> str:
    return email.strip().lower()

def create_password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()

def create_user(email: str, password: str) -> dict:
    db = get_db()
    users = db["users"]

    normalized_email = normalize_email(email)

    existing_user = users.find_one({"email": normalized_email})
    if existing_user is not None:
        raise ValueError("Email already exists")

    salt = secrets.token_hex(16)
    password_hash = create_password_hash(password, salt)

    user_doc = {
        "email": normalized_email,
        "password_hash": password_hash,
        "password_salt": salt,
        "created_at": datetime.now()
    }

    result = users.insert_one(user_doc)

    return {
        "user_id": str(result.inserted_id),
        "email": normalized_email
    }

def authenticate_user(email: str, password: str) -> Optional[dict]:
    db = get_db()
    users = db["users"]

    normalized_email = normalize_email(email)
    user = users.find_one({"email": normalized_email})

    if user is None:
        return None

    password_hash = create_password_hash(password, user["password_salt"])

    if password_hash != user["password_hash"]:
        return None

    return {
        "user_id": str(user["_id"]),
        "email": user["email"]
    }

def create_access_token() -> str:
    return secrets.token_urlsafe(32)