from pydantic import BaseModel
from typing import List
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    username: str
    full_name: str
    role: str
    permissions: List[str] = []
    password: str

class Userlogin(UserBase):
    password: str

class User(UserBase):
    username: str
    full_name: str
    disabled: bool = False

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str = None