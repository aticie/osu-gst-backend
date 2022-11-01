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
    osu_id: int
    osu_username: str
    osu_avatar_url: str
    osu_global_rank: int


class PartialUser(UserBase):
    ...

    class Config:
        orm_mode = True


class PartialUserCreate(PartialUser):
    ...


class UserCreate(UserBase):
    discord_id: str


class User(PartialUser):
    id: str
    discord_id: str
    team: Team | None = None

    class Config:
        orm_mode = True
