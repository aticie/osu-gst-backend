import os
from typing import Optional, Union

import aiohttp
import jwt
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from dbsql import crud, models, schemas
from dbsql.database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/osu-identify", response_class=RedirectResponse)
async def osu_identify(code: str, state: Optional[str] = None) -> Union[RedirectResponse, HTTPException]:
    try:
        state_dict = jwt.decode(state, os.getenv("JWT_KEY"), algorithms="HS256")
        redirect_to = state_dict["redirect_to"]
        response = RedirectResponse(url=redirect_to)
    except Exception as e:
        return HTTPException(500, f"Something went wrong, show this to the developers.\n{e}")

    token_body = {
        "code": code,
        "client_id": os.getenv("OSU_CLIENT_ID"),
        "client_secret": os.getenv("OSU_CLIENT_SECRET"),
        "grant_type": "authorization_code",
        "redirect_uri": os.getenv("REDIRECT_URI") + "/osu-identify"
    }
    async with aiohttp.ClientSession() as sess:
        async with sess.post(r"https://osu.ppy.sh/oauth/token", json=token_body) as resp:
            contents = await resp.json()

        access_token = contents.get("access_token")
        if not access_token:
            return HTTPException(500, "Something went wrong with the authentication...")

        headers = {"Authorization": f"Bearer {access_token}"}
        async with sess.get(r"https://osu.ppy.sh/api/v2/me", headers=headers) as resp:
            me_result = await resp.json()
            for k, v in me_result.items():
                response.set_cookie(key=f"osu_{k}", value=v)

    return response


@app.get("/discord-identify")
async def discord_identify(code: str, state: Optional[str] = None):
    try:
        state_dict = jwt.decode(state, os.getenv("JWT_KEY"), algorithms="HS256")
        redirect_to = state_dict["redirect_to"]
        response = RedirectResponse(url=redirect_to)
    except Exception as e:
        return HTTPException(500, f"Something went wrong, show this to the developers.\n{e}")

    token_body = {
        "code": code,
        "client_id": os.getenv("DISCORD_CLIENT_ID"),
        "client_secret": os.getenv("DISCORD_CLIENT_SECRET"),
        "grant_type": "authorization_code",
        "redirect_uri": os.getenv("REDIRECT_URI") + "/discord-identify"
    }
    async with aiohttp.ClientSession() as sess:
        async with sess.post(r"https://discord.com/api/oauth2/token", data=token_body) as resp:
            contents = await resp.json()

        access_token = contents.get("access_token")
        if not access_token:
            return HTTPException(500, "Something went wrong with the authentication...")

        headers = {"Authorization": f"Bearer {access_token}"}
        async with sess.get(r"https://discord.com/api/v10/users/@me", headers=headers) as resp:
            me_result = await resp.json()
            for k, v in me_result.items():
                response.set_cookie(key=f"discord_{k}", value=v)

    return response


@app.post("/full-register/", response_model=schemas.User)
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_discord_id(db, discord_id=user.discord_id)
    if db_user:
        raise HTTPException(status_code=400, detail="User already registered")
    return crud.create_user(db=db, user=user)


@app.get("/users/", response_model=list[schemas.User])
async def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", response_model=schemas.User)
async def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.post("/users/{user_id}/items/", response_model=schemas.Team)
async def create_item_for_user(
        user_id: int, item: schemas.TeamCreate, db: Session = Depends(get_db)
):
    return crud.create_user_item(db=db, item=item, user_id=user_id)


@app.get("/teams/", response_model=list[schemas.Team])
async def read_teams(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = crud.get_teams(db, skip=skip, limit=limit)
    return items
