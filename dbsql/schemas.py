from typing import List

from pydantic import BaseModel, validator


class TeamBase(BaseModel):
    title: str

    @validator('title')
    def title_must_match_the_rules(cls, v):
        if len(v) > 16:
            raise ValueError('Title cannot be longer than 16 characters.')
        for c in v:
            if ord(c) < 32 or ord(c) > 126:
                raise ValueError('Title contains excluded characters.')

        return v

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
    is_banned: bool
    is_admin: bool
    ...


class TeamlessUser(UserCreate):
    ...


class PlayerlessTeam(TeamBase):
    team_hash: str
    avatar_url: str | None = None


class User(UserCreate):
    team: PlayerlessTeam | None = None

    class Config:
        orm_mode = True


class TeamCreate(TeamBase):
    ...


class Team(PlayerlessTeam):
    players: List[TeamlessUser] = []

    class Config:
        orm_mode = True


class Invite(BaseModel):
    team: PlayerlessTeam
    inviter: TeamlessUser
    invited: TeamlessUser

    class Config:
        orm_mode = True
