import models
from facade.base_facade import BaseFacade
from fastapi import HTTPException, status
import schemas
from sqlalchemy.future import select
from typing import List


class ContainerFacade(BaseFacade):
    async def create_container(self, user_id: int, file_path: str) -> models.Container:
        db_container = models.Container(
            user_id=user_id,
            file_path=file_path,
        )

        self.db.add(db_container)
        await self.db.commit()
        await self.db.refresh(db_container)
        return db_container

    async def get_container(self, container_id: int) -> models.Container:
        container = await self.db.get(models.Container, container_id)
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        return container

    async def get_containers_by_user(self, user_id: int) -> List[schemas.Container]:
        async with self.db as session:
            containers = (
                await session.execute(
                    select(models.Container)
                    .where(models.Container.user_id == user_id)
                )
            ).scalars().all()
            return containers


container_facade = ContainerFacade()