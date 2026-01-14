# app/auth/router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

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
)

router = APIRouter(prefix="/auth", tags=["auth"])


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

    db.add(RefreshSession(
        id_user=user.id_user,
        token_hash=hash_refresh(refresh),
        expires_at=refresh_expires_at(),
    ))
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

    db.add(RefreshSession(
        id_user=user.id_user,
        token_hash=hash_refresh(refresh),
        expires_at=refresh_expires_at(),
    ))
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

    sess = db.query(RefreshSession).filter(
        RefreshSession.token_hash == token_h
    ).first()

    if not sess or sess.revoked_at or sess.expires_at <= now:
        raise HTTPException(401, "Invalid refresh token")

    user = db.query(User).filter(User.id_user == sess.id_user).first()
    if not user:
        raise HTTPException(401, "Invalid session")

    new_refresh = create_refresh_token()
    new_hash = hash_refresh(new_refresh)

    sess.revoked_at = now
    sess.replaced_by_hash = new_hash

    db.add(RefreshSession(
        id_user=user.id_user,
        token_hash=new_hash,
        expires_at=refresh_expires_at(),
    ))
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
    sess = db.query(RefreshSession).filter(
        RefreshSession.token_hash == token_h
    ).first()

    if sess and not sess.revoked_at:
        sess.revoked_at = datetime.now(timezone.utc)
        db.commit()

    return {"ok": True}
