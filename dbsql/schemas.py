from pydantic import BaseModel


class TeamBase(BaseModel):
    title: str
    avatar_url: str | None = None


class TeamCreate(TeamBase):
    ...


class Team(TeamBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    ...


class OsuUser(UserBase):
    osu_id: int
    osu_username: str
    osu_avatar_url: str
    osu_global_rank: int | None = None

    class Config:
        orm_mode = True


class OsuUserCreate(OsuUser):
    user_hash: str
    ...


class DiscordUser(UserBase):
    discord_id: str
    discord_avatar_url: str
    discord_tag: str


class UserCreate(OsuUser, DiscordUser):
    ...


class User(UserCreate):
    team: Team | None = None

    class Config:
        orm_mode = True
