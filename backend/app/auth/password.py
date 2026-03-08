import bcrypt

# bcrypt en fazla 72 byte kabul eder
MAX_PASSWORD_BYTES = 72


def _to_bytes(password: str) -> bytes:
    raw = password.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        raw = raw[:MAX_PASSWORD_BYTES]
    return raw


def hash_password(password: str) -> str:
    pw = _to_bytes(password)
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(plain), hashed.encode("utf-8"))
    except Exception:
        return False
