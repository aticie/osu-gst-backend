from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
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
    team_hash = Column(String, ForeignKey("teams.team_hash"))

    team = relationship("Team", back_populates="players")


class Team(Base):
    __tablename__ = "teams"

    team_hash = Column(String, primary_key=True, index=True)
    title = Column(String, index=True, unique=True)
    avatar_url = Column(String)

    players = relationship("User", back_populates="team")


class Invite(Base):
    __tablename__ = "invites"

    id = Column(Integer, primary_key=True, index=True)
    user_hash = Column(String, ForeignKey("users.user_hash"))
    team_hash = Column(String, ForeignKey("teams.team_hash"))
