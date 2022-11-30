import datetime
import hashlib
import os
import uuid
from typing import List, Optional

import aiohttp
from fastapi import Depends, FastAPI, HTTPException, Cookie, UploadFile, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from dbsql import crud, models, schemas
from dbsql.database import SessionLocal, engine
from dbsql.schemas import OsuUserCreate, DiscordUser
from utils.image import check_image_is_in_formats, upload_binary_file_to_imgur

ONE_MONTH = 2592000
BADGE_WORD_FILTER = [
    "taiko",
    "catch",
    "mania",
    "mapping",
    "nominator",
    "nomination",
    "beatmap",
    "contribution",
    "mappers'",
    "mapper's",
    "mapper",
    "spotlight",
    "playlist",
    "fanart",
]

models.Base.metadata.create_all(bind=engine)

frontend_homepage = os.getenv("FRONTEND_HOMEPAGE")

if os.getenv("DEV"):
    app = FastAPI()
    origins = [
        "*"
    ]
else:
    app = FastAPI(docs_url=None, openapi_url=None, redoc_url=None)
    origins = [
        "https://www.gstlive.org",
        "http://www.gstlive.org",
        "https://gstlive.org",
        "http://gstlive.org",
    ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_content_length_exists(content_length: str | None = Header()):
    if not content_length:
        raise HTTPException(411)


def verify_content_less_than_max_size(content_length: str = Header()):
    max_upload_size = 10000000  # 10 MB
    file_size = int(content_length)
    if file_size > max_upload_size:
        raise HTTPException(413)


def user_is_admin(db: Session = Depends(get_db), user_hash: str | None = Cookie(default=None)):
    db_user = crud.get_user(db=db, user_hash=user_hash)
    if not db_user.is_admin:
        raise HTTPException(403, "You require admin privileges.")


def user_is_not_admin(db: Session = Depends(get_db), user_hash: str | None = Cookie(default=None)):
    if os.getenv("DEV"):
        return

    db_user = crud.get_user(db=db, user_hash=user_hash)
    if db_user.is_admin:
        raise HTTPException(403, "You are an admin, not a player.")


def user_is_not_banned(db: Session = Depends(get_db), user_hash: str | None = Cookie(default=None)):
    db_user = crud.get_user(db=db, user_hash=user_hash)
    if db_user.is_banned:
        raise HTTPException(403, "You are banned.")


def hash_with_secret(string_to_be_hashed: str) -> str:
    hash_secret = os.getenv("SECRET")
    return hashlib.md5(f"{string_to_be_hashed}+{hash_secret}".encode()).hexdigest()


def hash_with_random(string_to_be_hashed: str) -> str:
    hash_secret = uuid.uuid4()
    return hashlib.md5(f"{string_to_be_hashed}+{hash_secret}".encode()).hexdigest()


def sign_ups_open_period():
    if datetime.datetime.now() > datetime.datetime.fromisoformat("2022-11-27T16:00:00"):
        raise HTTPException(401, "Sign-ups are closed.")


async def oauth2_authorization(code: str,
                               client_id: str,
                               client_secret: str,
                               redirect_uri: str,
                               token_endpoint: str):
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
            raise HTTPException(500,
                                "Something went wrong with the authentication, didn't get access token...")

    return access_token


async def get_me_data(access_token, me_endpoint):
    headers = {"Authorization": f"Bearer {access_token}"}
    async with aiohttp.ClientSession(headers=headers) as sess:
        async with sess.get(me_endpoint) as resp:
            me_result = await resp.json()

    return me_result


@app.get("/osu-identify", response_class=RedirectResponse)
async def osu_identify(code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    access_token = await oauth2_authorization(code=code,
                                              client_id=os.getenv("OSU_CLIENT_ID"),
                                              client_secret=os.getenv("OSU_CLIENT_SECRET"),
                                              redirect_uri=os.getenv("REDIRECT_URI") + "/osu-identify",
                                              token_endpoint=r"https://osu.ppy.sh/oauth/token")
    me_result = await get_me_data(access_token, r"https://osu.ppy.sh/api/v2/me/osu")
    osu_id = me_result["id"]
    user_hash = hash_with_secret(osu_id)
    redirect = RedirectResponse(frontend_homepage)

    db_user = crud.get_user_by_osu_id(db=db, osu_id=osu_id)
    if db_user:
        redirect.set_cookie(key="user_hash", value=db_user.user_hash, max_age=ONE_MONTH)
        return redirect
    else:
        redirect.set_cookie(key="user_hash", value=user_hash, max_age=ONE_MONTH)

    global_rank = me_result["statistics"]["global_rank"]
    badges = me_result["badges"]

    num_badges = 0
    for badge in badges:
        badge_desc: str = badge["description"]
        description = badge_desc.casefold()

        # If description contains any word that is in filter
        if any(filter_word in description for filter_word in BADGE_WORD_FILTER):
            continue

        num_badges += 1

    num = global_rank if global_rank and global_rank >= 0 else 0
    bws_rank = round(num ** (0.9937 ** (num_badges ** 2)))

    user = OsuUserCreate(osu_id=osu_id,
                         osu_username=me_result["username"],
                         osu_avatar_url=me_result["avatar_url"],
                         osu_global_rank=me_result["statistics"]["global_rank"],
                         user_hash=user_hash,
                         bws_rank=bws_rank,
                         badges=num_badges)

    crud.create_osu_user(db=db, user=user)

    return redirect


@app.get("/discord-identify", response_class=RedirectResponse, dependencies=[Depends(sign_ups_open_period)])
async def discord_identify(code: str, db: Session = Depends(get_db),
                           user_hash: str | None = Cookie(default=None)):
    access_token = await oauth2_authorization(code=code,
                                              client_id=os.getenv("DISCORD_CLIENT_ID"),
                                              client_secret=os.getenv("DISCORD_CLIENT_SECRET"),
                                              redirect_uri=os.getenv("REDIRECT_URI") + "/discord-identify",
                                              token_endpoint=r"https://discord.com/api/oauth2/token")
    me_result = await get_me_data(access_token=access_token,
                                  me_endpoint=r"https://discord.com/api/v10/users/@me")
    user_id = me_result["id"]
    username = me_result["username"]
    discriminator = me_result["discriminator"]
    avatar_hash = me_result["avatar"]
    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
    user = DiscordUser(discord_id=user_id,
                       discord_avatar_url=avatar_url,
                       discord_tag=f"{username}#{discriminator}",
                       )
    crud.upgrade_to_discord_user(db=db, user_hash=user_hash, user=user)

    redirect = RedirectResponse(frontend_homepage)
    redirect.set_cookie(key="user", value=user_hash, max_age=ONE_MONTH)
    return redirect


@app.get("/users/me", response_model=schemas.User)
async def read_me(db: Session = Depends(get_db),
                  user_hash: str = Cookie(default=None)):
    user = crud.get_user(db=db, user_hash=user_hash)
    return user


@app.put("/users/me", response_model=schemas.User)
async def unlink_user_discord(db: Session = Depends(get_db),
                              user_hash: str = Cookie(default=None)):
    user = crud.downgrade_from_discord_user(db=db, user_hash=user_hash)
    return user


@app.get("/users/me/invites", response_model=List[schemas.Invite])
async def read_user_invites(db: Session = Depends(get_db),
                            user_hash: str = Cookie(default=None)):
    invites = crud.get_user_invites(db=db, user_hash=user_hash)
    return invites


@app.get("/users", response_model=List[schemas.User])
async def read_users(db: Session = Depends(get_db)):
    users = crud.get_users(db=db)
    return users


@app.post("/team", response_model=schemas.Team,
          dependencies=[Depends(user_is_not_banned), Depends(user_is_not_admin), Depends(sign_ups_open_period)])
async def create_team(team: schemas.TeamCreate, db: Session = Depends(get_db),
                      user_hash: str | None = Cookie(default=None)):
    team_hash = hash_with_random(user_hash)
    team = crud.create_team(db=db, team=team, user_hash=user_hash, team_hash=team_hash)

    return team


@app.delete("/team", response_model=schemas.User,
            dependencies=[Depends(user_is_not_banned), Depends(sign_ups_open_period)])
async def leave_team(db: Session = Depends(get_db),
                     user_hash: str | None = Cookie(default=None)):
    db_user = crud.leave_team(db=db, user_hash=user_hash)

    return db_user


@app.get("/team/invites", response_model=List[schemas.Invite])
async def read_team_invites(team_hash: str, db: Session = Depends(get_db)):
    return crud.get_team_invites(db=db, team_hash=team_hash)


@app.get("/teams", response_model=List[schemas.Team])
async def read_teams(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    teams = crud.get_teams(db, skip=skip, limit=limit)
    return teams


@app.post("/user/team/join", response_model=schemas.User,
          dependencies=[Depends(user_is_not_banned), Depends(sign_ups_open_period)])
async def user_join_team(team_hash: str, db: Session = Depends(get_db),
                         user_hash: str | None = Cookie(default=None)):
    db_user = crud.add_player_to_team(db=db, team_hash=team_hash, user_hash=user_hash)

    return db_user


@app.post("/user/lobby/join", response_model=schemas.Team, dependencies=[Depends(user_is_not_banned)])
async def add_user_to_lobby(lobby_id: int, db: Session = Depends(get_db),
                            user_hash: str | None = Cookie(default=None)):
    return crud.add_team_to_lobby(db=db, user_hash=user_hash, lobby_id=lobby_id)


@app.post("/user/lobby/leave", response_model=schemas.Team, dependencies=[Depends(user_is_not_banned)])
async def leave_from_lobby(db: Session = Depends(get_db),
                           user_hash: str | None = Cookie(default=None)):
    return crud.remove_team_from_lobby(db=db, user_hash=user_hash)


@app.post("/team/invite", response_model=schemas.Invite,
          dependencies=[Depends(user_is_not_banned), Depends(sign_ups_open_period)])
async def team_create_invite(other_user_osu_id: int,
                             db: Session = Depends(get_db),
                             user_hash: str | None = Cookie(default=None)):
    return crud.create_invite(db=db, team_owner_hash=user_hash, invited_user_osu_id=other_user_osu_id)


@app.delete("/team/invite", response_model=Optional[List[schemas.Invite]])
async def team_cancel_invite(other_user_osu_id: int,
                             db: Session = Depends(get_db),
                             user_hash: str | None = Cookie(default=None)):
    return crud.cancel_invite(db=db, user_hash=user_hash, invited_user_osu_id=other_user_osu_id)


@app.delete("/user/invite", response_model=schemas.User,
            dependencies=[Depends(user_is_not_banned), Depends(sign_ups_open_period)])
async def user_decline_invite(team_hash: str,
                              db: Session = Depends(get_db),
                              user_hash: str | None = Cookie(default=None)):
    return crud.decline_invite(db=db, user_hash=user_hash, team_hash=team_hash)


@app.post("/avatar/upload", response_model=schemas.Team,
          dependencies=[Depends(user_is_not_banned), Depends(verify_content_length_exists),
                        Depends(verify_content_less_than_max_size), Depends(sign_ups_open_period)])
async def create_avatar(file: UploadFile,
                        db: Session = Depends(get_db),
                        user_hash: str | None = Cookie(default=None)):
    if not check_image_is_in_formats(image_file=file.file,
                                     formats=['png', 'jpg', 'jpeg', 'gif']):
        raise HTTPException(400,
                            "Uploaded file must be one of the following formats: '.png', '.jpg', '.jpeg', or '.gif'")

    img_response = await upload_binary_file_to_imgur(file=file, imgur_client_id=os.getenv("IMGUR_CLIENT_ID"))
    img_url = img_response["link"]
    return crud.create_avatar(db=db, user_hash=user_hash, img_url=img_url)


@app.post("/user/ban", dependencies=[Depends(user_is_admin)], response_model=schemas.User)
async def ban_user(user_osu_id: int,
                   db: Session = Depends(get_db)):
    return crud.ban_user(db=db, user_osu_id=user_osu_id)


@app.delete("/user/ban", dependencies=[Depends(user_is_admin)], response_model=schemas.User)
async def unban_user(user_osu_id: int,
                     db: Session = Depends(get_db)):
    return crud.unban_user(db=db, user_osu_id=user_osu_id)


@app.get("/lobbies", response_model=Optional[List[schemas.Lobby]])
async def get_lobbies(db: Session = Depends(get_db)):
    return crud.get_lobbies(db=db)


@app.get("/lobby", response_model=Optional[schemas.Lobby])
async def get_lobby(lobby_id: int, db: Session = Depends(get_db)):
    return crud.get_lobby(db=db, lobby_id=lobby_id)


@app.delete("/lobby", dependencies=[Depends(user_is_admin)], response_model=Optional[schemas.Lobby])
async def remove_lobby(lobby_id: int, db: Session = Depends(get_db)):
    return crud.remove_lobby(db=db, lobby_id=lobby_id)


@app.post("/lobby/create", dependencies=[Depends(user_is_admin)], response_model=schemas.Lobby)
async def create_lobby(lobby_time: datetime.datetime, lobby_name: str,
                       db: Session = Depends(get_db), referee_osu_username: Optional[str] = None):
    return crud.create_lobby(db=db, referee_osu_username=referee_osu_username, lobby_time=lobby_time,
                             lobby_name=lobby_name)


@app.post("/lobby/add_referee", dependencies=[Depends(user_is_admin)], response_model=schemas.Lobby)
async def add_referee_to_lobby(referee_osu_username: str, lobby_id: int,
                               db: Session = Depends(get_db)):
    return crud.add_referee_to_lobby(db=db, referee_osu_username=referee_osu_username, lobby_id=lobby_id)
