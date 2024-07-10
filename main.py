from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from db.async_db import get_db
from facade.container_facade import container_facade
from routers import admin, auth, containers,token


def set_db_for_facades(db):
    container_facade.set_db(db)


OAuth2_SCHEME = OAuth2PasswordBearer('user/login/')

app = FastAPI()


@app.on_event('startup')
async def startup_event():
    async for db in get_db():
        set_db_for_facades(db)
        break


app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(containers.router)
app.include_router(token.router)




@app.get('/')
async def index():
    return {'message': 'Hello World'}