# app/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import jwt

from src.db import get_db
from src.models import User, RefreshSession
from src.auth.schemas import RegisterIn, LoginIn, RefreshIn, TokenOut
from src.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_refresh,
    refresh_expires_at,
    ACCESS_MIN,
    JWT_SECRET,
    JWT_ALG,
)

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency do autoryzacji.
    Oczekuje nagłówka: Authorization: Bearer <access_token>
    Zwraca obiekt User z bazy.
    """
    token = creds.credentials

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token",
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    user = db.query(User).filter(User.id_user == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    """
    Zwraca dane aktualnie zalogowanego usera (na podstawie access tokena).
    """
    return {
        "id_user": user.id_user,
        "username": user.username,
        "email": user.email,
        "nr_telefonu": user.nr_telefonu,
        "created_at": user.created_at,
    }


@router.post("/register", response_model=TokenOut, status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(409, "Username already exists")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(409, "Email already exists")

    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        nr_telefonu=data.nr_telefonu,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access = create_access_token(user.id_user)
    refresh = create_refresh_token()

    db.add(
        RefreshSession(
            id_user=user.id_user,
            token_hash=hash_refresh(refresh),
            expires_at=refresh_expires_at(),
        )
    )
    db.commit()

    return TokenOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=ACCESS_MIN * 60,
    )


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == data.login) | (User.email == data.login)
    ).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    access = create_access_token(user.id_user)
    refresh = create_refresh_token()

    db.add(
        RefreshSession(
            id_user=user.id_user,
            token_hash=hash_refresh(refresh),
            expires_at=refresh_expires_at(),
        )
    )
    db.commit()

    return TokenOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=ACCESS_MIN * 60,
    )


@router.post("/refresh", response_model=TokenOut)
def refresh_tokens(data: RefreshIn, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    token_h = hash_refresh(data.refresh_token)

    sess = db.query(RefreshSession).filter(RefreshSession.token_hash == token_h).first()

    if not sess or sess.revoked_at or sess.expires_at <= now:
        raise HTTPException(401, "Invalid refresh token")

    user = db.query(User).filter(User.id_user == sess.id_user).first()
    if not user:
        raise HTTPException(401, "Invalid session")

    new_refresh = create_refresh_token()
    new_hash = hash_refresh(new_refresh)

    sess.revoked_at = now
    # UWAGA: to pole musi istnieć w modelu RefreshSession, inaczej usuń tę linię:
    sess.replaced_by_hash = new_hash

    db.add(
        RefreshSession(
            id_user=user.id_user,
            token_hash=new_hash,
            expires_at=refresh_expires_at(),
        )
    )
    db.commit()

    new_access = create_access_token(user.id_user)

    return TokenOut(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=ACCESS_MIN * 60,
    )


@router.post("/logout")
def logout(data: RefreshIn, db: Session = Depends(get_db)):
    token_h = hash_refresh(data.refresh_token)
    sess = db.query(RefreshSession).filter(RefreshSession.token_hash == token_h).first()

    if sess and not sess.revoked_at:
        sess.revoked_at = datetime.now(timezone.utc)
        db.commit()

    return {"ok": True}


@router.post("/logout_all")
def logout_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Unieważnia wszystkie aktywne refresh tokeny danego użytkownika.
    """
    now = datetime.now(timezone.utc)

    db.query(RefreshSession).filter(
        RefreshSession.id_user == user.id_user,
        RefreshSession.revoked_at.is_(None),
    ).update(
        {RefreshSession.revoked_at: now},
        synchronize_session=False,
    )

    db.commit()
    return {"ok": True}
