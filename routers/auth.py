from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from db.async_db import get_db
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
import models
from schemas.auth import Token
from schemas import auth
from pathlib import Path
from services.auth import (get_user, create_access_token, create_refresh_token, authenticate_user,
                           create_password_reset_token)
from config import REFRESH_TOKEN_EXPIRE_DAYS, PWD_CONTEXT


router = APIRouter(
    prefix='/auth',
    tags=['Auth']
)

UPLOAD_DIRECTORY = 'static/containers/'
Path(UPLOAD_DIRECTORY).mkdir(parents=True, exist_ok=True)


@router.post('/register/', response_model=auth.User)
async def register(user: auth.UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await get_user(db, email=user.email)

    if db_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='User already exists!')

    hashed_password = PWD_CONTEXT.hash(user.password)
    db_user = models.User(
        email=user.email,
        password_hash=hashed_password,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post("/login/")
async def login(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...)
):
    user = await authenticate_user(db, username, password)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Invalid credentials"})

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token(user.id)

    response.set_cookie(key="access_token", value=access_token, httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)

    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)

    return {"access_token": access_token}



