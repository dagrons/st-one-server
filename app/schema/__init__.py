from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str


class SearchKWArgs(BaseModel):
    k: int = 20
    score_threshold: float = 0.2
    fetch_k: int = 4
    lambda_mult: float = 0.25
