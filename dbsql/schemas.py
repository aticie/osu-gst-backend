import datetime
from typing import List, Optional

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


class Lobby(BaseModel):
    id: int
    lobby_name: str
    referee: Optional[str]
    date: datetime.datetime
    teams: List[Team]

    class Config:
        orm_mode = True


class Mappool(BaseModel):
    id: str
    mods: str
    title: str
    raw_title: str
    sr: float
    bpm: int
    cs: float
    ar: float
    od: float
    mapset: str
    set_id: int
    map_id: int
    youtube: str

    class Config:
        orm_mode = True


class OverallPlayerScore(BaseModel):
    username: str
    score: Optional[float]

    class Config:
        orm_mode = True


class OverallTeamScore(BaseModel):
    teamname: str
    score: Optional[float]
    zscore: Optional[float]

    class Config:
        orm_mode = True


class TeamMapScore(OverallTeamScore):
    map_id: str


class PlayerMapScore(OverallPlayerScore):
    map_id: str
