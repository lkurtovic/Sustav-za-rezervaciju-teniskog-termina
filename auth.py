from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from typing import Optional

# NZ-03: Postavka za b-crypt hashiranje lozinki
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Tajni ključ za potpisivanje tokena (promijeni ovo u nešto nasumično kasnije)
SECRET_KEY = "super-tajna-sifra-za-projekt"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)