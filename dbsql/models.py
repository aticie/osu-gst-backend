from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Float
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    user_hash = Column(String, primary_key=True, unique=True)
    osu_id = Column(Integer, unique=True, index=True)
    osu_avatar_url = Column(String)
    osu_username = Column(String, unique=True)
    osu_global_rank = Column(Integer, nullable=True)
    discord_id = Column(String, unique=True, index=True)
    discord_avatar_url = Column(String)
    discord_tag = Column(String)
    discord_linked = Column(Boolean, default=False)
    osu_linked = Column(Boolean, default=False)
    bws_rank = Column(Integer)
    badges = Column(Integer)
    is_banned = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    team_hash = Column(String, ForeignKey("teams.team_hash"))

    team = relationship("Team", back_populates="players")


class Team(Base):
    __tablename__ = "teams"

    team_hash = Column(String, primary_key=True, index=True)
    title = Column(String, index=True, unique=True)
    avatar_url = Column(String)
    lobby_id = Column(Integer, ForeignKey("lobbies.id"))
    lobby = relationship("QualifierLobby", back_populates="teams")

    players = relationship("User", back_populates="team")


class Invite(Base):
    __tablename__ = "invites"

    id = Column(Integer, primary_key=True, index=True)
    invited_user_hash = Column(String, ForeignKey("users.user_hash"))
    inviter_user_hash = Column(String, ForeignKey("users.user_hash"))
    team_hash = Column(String, ForeignKey("teams.team_hash"))

    team = relationship("Team")
    inviter = relationship("User", foreign_keys=[inviter_user_hash])
    invited = relationship("User", foreign_keys=[invited_user_hash])


class QualifierLobby(Base):
    __tablename__ = "lobbies"

    id = Column(Integer, primary_key=True, index=True)
    lobby_name = Column(String)
    referee = Column(String, nullable=True)

    date = Column(DateTime)
    teams = relationship("Team", back_populates="lobby")


class Mappools(Base):
    __tablename__ = "mappools"

    _id = Column(Integer, primary_key=True)
    id = Column("id", String, index=True)
    mods = Column("mods", String)
    title = Column("artist - title [difficulty]", String)
    raw_title = Column("RAW artist - title [difficulty]", String)
    sr = Column("sr", Float)
    bpm = Column("bpm", Integer)
    length = Column("length", DateTime(timezone=False))
    cs = Column("cs", String)
    ar = Column("ar", String)
    od = Column("od", String)
    mapset = Column("mapset", String)
    set_id = Column("set id", Integer)
    map_id = Column("map id", Integer)
    youtube = Column("youtube", String, nullable=True)
    type = Column("type", String)


class TeamScore(Base):
    __tablename__ = "team_scores"

    index = Column(Integer, primary_key=True, index=True)

    teamname = Column(String, ForeignKey("teams.title"))
    team = relationship("Team")

    map_id = Column(String, ForeignKey("mappools.id"))
    map = relationship("Mappools")

    score = Column(Integer, nullable=True)
    zscore = Column(Integer, nullable=True)


class PlayerScore(Base):
    __tablename__ = "player_scores"

    index = Column(Integer, primary_key=True, index=True)

    username = Column(String, ForeignKey("users.osu_username"))
    user = relationship("User")

    map_id = Column(String, ForeignKey("mappools.id"))
    map = relationship("Mappools")

    score = Column(Integer, nullable=True)
