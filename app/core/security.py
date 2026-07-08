import datetime as dt
import jwt
from jwt import PyJWTError


def create_access_token(
    subject: str,
    secret: str,
    issuer: str,
    expires_minutes: int = 60,
    role: str | None = None,
) -> str:
    now = dt.datetime.utcnow()
    payload = {
        "sub": subject,
        "iss": issuer,
        "iat": now,
        "exp": now + dt.timedelta(minutes=expires_minutes),
    }
    if role:
        payload["role"] = role
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str, secret: str, issuer: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=["HS256"], issuer=issuer)
    except PyJWTError as exc:
        raise ValueError("Invalid token") from exc
