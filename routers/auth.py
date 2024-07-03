from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response
from db.async_db import get_db
from typing import List
from sqlalchemy.future import select
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
import models
from schemas.auth import Token
from schemas import auth
from pathlib import Path
from services.auth import (get_user, create_access_token, create_refresh_token, authenticate_user,
                           create_password_reset_token, )
from config import ALGORITHM, REFRESH_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS


PWD_CONTEXT = CryptContext(schemes=['bcrypt'], deprecated='auto')
OAuth2_SCHEME = OAuth2PasswordBearer(tokenUrl='auth/login')

router = APIRouter(
    prefix='/auth',
    tags=['Auth']
)

UPLOAD_DIRECTORY = 'static/containers/'
Path(UPLOAD_DIRECTORY).mkdir(parents=True, exist_ok=True)


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):

    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=15))
    refresh_token = create_refresh_token(data={"sub": user.email}, expires_delta=timedelta(days=7))
    user.refresh_token = refresh_token
    await db.commit()

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/token/refresh", response_model=Token)
async def refresh_token(reset_token: str, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(reset_token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await db.execute(select(models.User).filter(models.User.email == email))
        user = user.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        new_access_token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=15))

        new_refresh_token = create_refresh_token(data={"sub": user.email}, expires_delta=timedelta(days=7))
        user.refresh_token = new_refresh_token
        await db.commit()

        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


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


@router.post('/login/', response_model=auth.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password',
            headers={'WWW-Authenticate': 'Bearer'}
        )

    access_token_expire = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expire = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(
        data={'sub': user.email}, expires_delta=access_token_expire
    )
    refresh_token = create_refresh_token(
        data={'sub': user.email}, expires_delta=refresh_token_expire
    )

    return {'access_token': access_token, 'refresh_token': refresh_token, 'token_type': 'bearer'}




