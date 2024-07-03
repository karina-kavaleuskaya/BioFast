from fastapi import Depends, HTTPException, status, Request, Response
from db.async_db import get_db
from sqlalchemy.future import select
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import models
from config import ALGORITHM, SECRET_KEY, REFRESH_SECRET_KEY, REFRESH_TOKEN_EXPIRE_DAYS, ACCESS_TOKEN_EXPIRE_MINUTES


PWD_CONTEXT = CryptContext(schemes=['bcrypt'], deprecated='auto')
OAuth2_SCHEME = OAuth2PasswordBearer(tokenUrl='auth/login')


async def get_user(db:AsyncSession, email):
    async with db:
        result = await db.execute(select(models.User).filter(models.User.email == email))
        return result.scalars().first()


def verify_password(plain_password, hashed_password):
    return PWD_CONTEXT.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta):
    data_to_process = data.copy()
    expire = datetime.utcnow() + expires_delta
    data_to_process.update({'exp': expire})
    encode_jwt = jwt.encode(data_to_process, SECRET_KEY, algorithm=ALGORITHM)
    return encode_jwt


def create_refresh_token(data: dict, expires_delta: timedelta):
    data_to_process = data.copy()
    expire = datetime.utcnow() + expires_delta
    data_to_process.update({'exp': expire})
    refresh_token = jwt.encode(data_to_process, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return refresh_token


async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await get_user(db, email)
    if not user or not verify_password(password, user.password_hash):
        return False
    return user


def create_password_reset_token(data: dict):
    return jwt.encode(data, REFRESH_SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    request: Request,
    token: str = Depends(OAuth2_SCHEME),
    db: AsyncSession = Depends(get_db)
):

    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'}
    )

    try:
        access_payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": True})
        email: str = access_payload.get('sub')
        if not email:
            raise credential_exception

        user = await db.execute(select(models.User).where(models.User.email == email))
        user = user.scalars().first()
        if not user:
            raise credential_exception

        return user

    except jwt.ExpiredSignatureError:
        refresh_token = get_refresh_token(request)
        if refresh_token:
            try:
                refresh_payload = jwt.decode(refresh_token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
                email = refresh_payload.get('sub')
                if email:
                    user = await db.execute(select(models.User).where(models.User.email == email))
                    user = user.scalars().first()
                    if user:
                        access_token_data = {'sub': user.email}
                        new_access_token = create_access_token(data=access_token_data,
                                                               expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
                        return user
                    else:

                        raise credential_exception
                else:
                    raise credential_exception
            except JWTError as e:
                raise credential_exception
        else:
            raise credential_exception
    except JWTError as e:
        raise credential_exception


async def refresh_access_token(request: Request, db: AsyncSession):
    refresh_token = get_refresh_token(request)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found")

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user = await db.get(models.User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        access_token = create_access_token(user)
        new_refresh_token = create_refresh_token(user)
        save_refresh_token(request.app.state.Response, new_refresh_token)
        return access_token
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Error refreshing access token")


def save_refresh_token(response: Response, refresh_token: str):
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="strict",
    )


def get_refresh_token(request: Request):
    return request.cookies.get("refresh_token")