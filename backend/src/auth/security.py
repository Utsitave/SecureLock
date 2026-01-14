import hashlib, secrets
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = "to_nie_ja_to_chat"         # najlepiej z env
JWT_ALG = "HS256"
ACCESS_MIN = 15
REFRESH_DAYS = 30
JWT_ISS = "your-api"

def hash_password(p: str) -> str:
    return pwd_context.hash(p)

def verify_password(p: str, hashed: str) -> bool:
    return pwd_context.verify(p, hashed)

def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iss": JWT_ISS,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_MIN)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)

def hash_refresh(rt: str) -> str:
    return hashlib.sha256(rt.encode("utf-8")).hexdigest()

def refresh_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_DAYS)
