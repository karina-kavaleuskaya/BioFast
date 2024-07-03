from pydantic import BaseModel


class ContainerBase(BaseModel):
    user_id: int

    class Config:
        from_attributes = True


class ContainerCreate(ContainerBase):

    class Config:
        from_attributes = True


class Container(ContainerBase):
    id: int

    class Config:
        from_attributes = True