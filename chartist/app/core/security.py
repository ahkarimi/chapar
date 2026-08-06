from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from app.config import settings
import secrets
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, HTTPException, status

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/login")


def create_access_token(data: dict):
    if not settings.JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be configured before issuing tokens")
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def verify_token(token: str):
    if not settings.JWT_SECRET:
        return None
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


# Create a security instance for HTTP Basic auth
basic_security = HTTPBasic()


def verify_docs_credentials(
    credentials: HTTPBasicCredentials = Depends(basic_security),
):
    correct_username = secrets.compare_digest(
        credentials.username, settings.DOCS_USERNAME
    )
    correct_password = secrets.compare_digest(
        credentials.password, settings.DOCS_PASSWORD
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials for docs",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
