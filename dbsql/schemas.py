from typing import List

from pydantic import BaseModel


class TeamBase(BaseModel):
    title: str
    team_hash: str
    avatar_url: str | None = None

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    ...


class OsuUser(UserBase):
    osu_id: int
    osu_username: str
    osu_avatar_url: str
    osu_global_rank: int | None = None
    bws_rank: int | None = None
    badges: int = 0

    class Config:
        orm_mode = True


class OsuUserCreate(OsuUser):
    user_hash: str
    ...


class DiscordUser(UserBase):
    discord_id: str | None
    discord_avatar_url: str | None
    discord_tag: str | None


class UserCreate(OsuUser, DiscordUser):
    ...


class TeamlessUser(UserCreate):
    ...


class User(UserCreate):
    team: TeamBase | None = None

    class Config:
        orm_mode = True


class TeamCreate(TeamBase):
    ...


class Team(TeamBase):
    players: List[TeamlessUser] = []

    class Config:
        orm_mode = True


class Invite(BaseModel):
    team: TeamBase
    inviter: TeamlessUser
    invited: TeamlessUser

    class Config:
        orm_mode = True
