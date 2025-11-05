from datetime import datetime, timedelta
from jose import jwt

ALGO = "HS256"

def create_access_token(subject: str, secret: str, expires_minutes: int = 60):
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, secret, algorithm=ALGO)
