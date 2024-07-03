import models
import os
import schemas
from typing import List
from users import get_current_user
from fastapi import HTTPException, Depends, APIRouter, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from async_db import get_db
from sqlalchemy.future import select
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix='/admin',
    tags=['Admin']
)


class EmailConfig:
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_FROM = os.getenv('MAIL_FROM')
    MAIL_PORT = int(os.getenv('MAIL_PORT'))
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_FROM_NAME = os.getenv('MAIL_FROM_NAME')


# Set up the FastAPI Mail connection configuration
conf = ConnectionConfig(
    MAIL_USERNAME=EmailConfig.MAIL_USERNAME,
    MAIL_PASSWORD=EmailConfig.MAIL_PASSWORD,
    MAIL_FROM=EmailConfig.MAIL_FROM,
    MAIL_PORT=EmailConfig.MAIL_PORT,
    MAIL_SERVER=EmailConfig.MAIL_SERVER,
    MAIL_FROM_NAME=EmailConfig.MAIL_FROM_NAME,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
)


@router.get('/users/', response_model=List[schemas.UserWithFiles])
async def get_users(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can access this endpoint.")

    async with db:
        result = await db.execute(select(models.User))
        users = result.scalars().all()

    result = []
    for user in users:
        user_dir = f'static/containers/{user.id}/'
        if os.path.exists(user_dir):
            files = os.listdir(user_dir)
        else:
            files = []
        result.append(schemas.UserWithFiles(id=user.id, email=user.email, files=files))
    return result


@router.post('/send-email/{user_id}')
async def send_user_email(
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can access this endpoint.")

    async with db:
        result = await db.execute(select(models.User).where(models.User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

    file_path = f'static/containers/{user.id}/'
    txt_files = [f for f in os.listdir(file_path) if f.endswith('.txt')]
    if not txt_files:
        raise HTTPException(status_code=404, detail="No .txt file found for this user.")

    # Формируем сообщение
    subject = f"User {user.id} File"
    body = f"Dear {user.email},\n\nPlease find the attached file for user {user.id}."
    message = MessageSchema(
        subject=subject,
        recipients=[user.email],
        body=body,
        attachments=[f"{file_path}{txt_files[0]}"],
        subtype='html'
    )

    fm = FastMail(conf)
    await fm.send_message(message)

    return {"message": "Email sent successfully"}