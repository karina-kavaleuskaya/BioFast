import models
import os
from schemas import auth
from typing import List
from services.auth import get_current_user
from fastapi import HTTPException, Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from db.async_db import get_db
from sqlalchemy.future import select
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix='/admin',
    tags=['Admin']
)


@router.get('/users/', response_model=List[auth.UserWithFiles])
async def get_users(
    name: str | None = None,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can access this endpoint.")

    async with db:
        query = select(models.User)

        if name is not None:
            query = query.filter(
                models.User.email.ilike(f'%{name}%')
            )

        result = await db.execute(query)
        users = result.scalars().all()

    response = []
    for user in users:
        user_dir = f'static/containers/{user.id}/'
        if os.path.exists(user_dir):
            files = os.listdir(user_dir)
        else:
            files = []
        response.append(auth.UserWithFiles(id=user.id, email=user.email, files=files))

    return response


