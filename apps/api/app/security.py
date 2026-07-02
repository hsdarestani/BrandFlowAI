from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from .database import settings
pwd_context=CryptContext(schemes=['bcrypt'], deprecated='auto')
def hash_password(p:str)->str: return pwd_context.hash(p)
def verify_password(p,h)->bool: return pwd_context.verify(p,h)
def create_token(sub:str)->str: return jwt.encode({'sub':sub,'exp':datetime.now(timezone.utc)+timedelta(days=7)}, settings.jwt_secret, algorithm='HS256')
def decode_token(t:str): return jwt.decode(t, settings.jwt_secret, algorithms=['HS256'])
