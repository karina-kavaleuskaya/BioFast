from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response
from db.async_db import get_db
from typing import List
from sqlalchemy.future import select
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import models
from schemas import auth, containers
from facade.file_facade import FILE_MANAGER
from facade.container_facade import container_facade
from pathlib import Path
import os
from services.auth import get_current_user





PWD_CONTEXT = CryptContext(schemes=['bcrypt'], deprecated='auto')
ALGORITHM = 'HS256'
SECRET_KEY = 'cfghjmnbvcdxfghnm'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
OAuth2_SCHEME = OAuth2PasswordBearer(tokenUrl='users/login')

router = APIRouter(
    prefix='/containers',
    tags=['Containers']
)

UPLOAD_DIRECTORY = 'static/containers/'
Path(UPLOAD_DIRECTORY).mkdir(parents=True, exist_ok=True)

@router.post('/add-file/', response_model=containers.ContainerCreate)
async def create_container(
        file: UploadFile = File(...),
        current_user: models.User = Depends(get_current_user),
):
    file_path = f'{current_user.id}/{file.filename}'
    await FILE_MANAGER.save_file(file, file_path)

    db_container = await container_facade.create_container(current_user.id, file_path)

    return db_container

@router.get('/container', response_model=List[containers.Container])
async def user_containers(
        current_user: models.User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    containers = await container_facade.get_containers_by_user(current_user.id)
    return containers


@router.get('/get_result/download')
async def download_files(container_id: int,
                         current_user: models.User = Depends(get_current_user)):
    try:
        container = await container_facade.get_container(container_id)
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Container not found')
        else:
            raise e

    if container.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='You are not authorized to access this container')

    file_data = await FILE_MANAGER.get_file(str(container.user_id), container.file_path)

    if not file_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='File not found')

    fast_file = os.path.basename(container.file_path)

    if fast_file.endswith("_analysis.txt"):
        file_name = fast_file
    else:
        file_name = os.path.splitext(fast_file)[0] + "_analysis.txt"

    return Response(content=file_data,
                    media_type='application/octet-stream',
                    headers={'Content-Disposition': f"attachment; filename={file_name}"})


