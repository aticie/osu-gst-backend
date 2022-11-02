import hashlib
import os
from typing import Union

import aiohttp
from fastapi import Depends, FastAPI, HTTPException, Cookie
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from dbsql import crud, models, schemas
from dbsql.database import SessionLocal, engine
from dbsql.schemas import OsuUserCreate, DiscordUser

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def oauth2_authorization(code: str,
                               client_id: str,
                               client_secret: str,
                               redirect_uri: str,
                               token_endpoint: str,
                               me_endpoint: str):
    token_body = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    async with aiohttp.ClientSession() as sess:
        async with sess.post(token_endpoint, data=token_body) as resp:
            contents = await resp.json()

        access_token = contents.get("access_token")
        if not access_token:
            return HTTPException(500,
                                 {"Status": "Something went wrong with the authentication, didn't get access token..."})

        headers = {"Authorization": f"Bearer {access_token}"}
        async with sess.get(me_endpoint, headers=headers) as resp:
            me_result = await resp.json()

    return me_result


@app.get("/osu-identify", response_class=RedirectResponse)
async def osu_identify(code: str, db: Session = Depends(get_db)) -> Union[RedirectResponse, HTTPException]:
    me_result = await oauth2_authorization(code=code,
                                           client_id=os.getenv("OSU_CLIENT_ID"),
                                           client_secret=os.getenv("OSU_CLIENT_SECRET"),
                                           redirect_uri=os.getenv("REDIRECT_URI") + "/osu-identify",
                                           token_endpoint=r"https://osu.ppy.sh/oauth/token",
                                           me_endpoint=r"https://osu.ppy.sh/api/v2/me")
    osu_id = me_result["id"]
    hash_secret = os.getenv("SECRET")
    user_hash = hashlib.md5(f"{osu_id}+{hash_secret}".encode()).hexdigest()

    user = OsuUserCreate(osu_id=osu_id,
                         osu_username=me_result["username"],
                         osu_avatar_url=me_result["avatar_url"],
                         osu_global_rank=me_result["statistics"]["global_rank"],
                         user_hash=user_hash)
    crud.create_osu_user(db=db, user=user)

    redirect = RedirectResponse(os.getenv("FRONTEND_HOMEPAGE"))
    redirect.set_cookie(key="user_hash", value=user_hash, max_age=2592000)
    return redirect


@app.get("/discord-identify")
async def discord_identify(code: str, db: Session = Depends(get_db),
                           user_hash: str | None = Cookie(default=None)):
    me_result = await oauth2_authorization(code=code,
                                           client_id=os.getenv("DISCORD_CLIENT_ID"),
                                           client_secret=os.getenv("DISCORD_CLIENT_SECRET"),
                                           redirect_uri=os.getenv("REDIRECT_URI") + "/discord-identify",
                                           token_endpoint=r"https://discord.com/api/oauth2/token",
                                           me_endpoint=r"https://discord.com/api/v10/users/@me")

    id = me_result["id"]
    username = me_result["username"]
    discriminator = me_result["discriminator"]
    avatar_hash = me_result["avatar"]
    avatar_url = f"https://cdn.discordapp.com/avatars/{id}/{avatar_hash}.png"
    user = DiscordUser(discord_id=id,
                       discord_avatar_url=avatar_url,
                       discord_tag=f"{username}#{discriminator}",
                       )
    crud.upgrade_to_discord_user(db=db, user_hash=user_hash, user=user)

    redirect = RedirectResponse(os.getenv("FRONTEND_HOMEPAGE"))
    redirect.set_cookie(key="user", value=user_hash, max_age=2592000)
    return redirect


@app.post("/full-register/", response_model=schemas.User)
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_discord_id(db, discord_id=user.discord_id)
    if db_user:
        raise HTTPException(status_code=400, detail="User already registered")
    return crud.create_osu_user(db=db, user=user)


@app.get("/users/me", response_model=list[schemas.User])
async def read_users(db: Session = Depends(get_db),
                     user_hash: str | None = Cookie(default=None)):
    user = crud.get_user(db, user_hash)
    return user


@app.get("/teams/", response_model=list[schemas.Team])
async def read_teams(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = crud.get_teams(db, skip=skip, limit=limit)
    return items
