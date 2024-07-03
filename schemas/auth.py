from typing import List
from pydantic import BaseModel, validator
from fastapi import HTTPException, status


class UserBase(BaseModel):
    email: str

    @validator('email')
    def email_must_be_valid(cls, v):
        import re
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', v):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid email address"
            )
        return v

    class Config:
        from_attributes = True


class UserCreate(UserBase):
    password:str


class User(UserBase):
    id: int


class Token(BaseModel):
    access_token: str
    token_type: str



class UserWithFiles(User):
    files: List[str]