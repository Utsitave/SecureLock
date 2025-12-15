# app/auth/schemas.py
from pydantic import BaseModel, EmailStr

class RegisterIn(BaseModel):
    username: str
    email: EmailStr
    password: str
    nr_telefonu: str | None = None

class LoginIn(BaseModel):
    login: str        # username albo email
    password: str

class RefreshIn(BaseModel):
    refresh_token: str

class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
