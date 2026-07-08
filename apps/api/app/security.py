from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from .database import settings

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(p: str) -> str:
    return pwd_context.hash(p)


def verify_password(p, h) -> bool:
    return pwd_context.verify(p, h)


def create_token(sub: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'sub': sub,
        'iat': now,
        'exp': now + timedelta(minutes=settings.jwt_expires_minutes),
        'iss': settings.jwt_issuer,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm='HS256')


def decode_token(t: str):
    return jwt.decode(
        t,
        settings.jwt_secret,
        algorithms=['HS256'],
        issuer=settings.jwt_issuer,
    )
