from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_hash = Column(String, index=True, unique=True)
    osu_id = Column(Integer, unique=True, index=True)
    osu_avatar_url = Column(String)
    osu_username = Column(String, unique=True)
    osu_global_rank = Column(Integer, nullable=True)
    discord_id = Column(String, unique=True, index=True)
    discord_avatar_url = Column(String)
    discord_tag = Column(String)
    discord_linked = Column(Boolean, default=False)
    osu_linked = Column(Boolean, default=False)
    team_id = Column(Integer, ForeignKey("teams.id"))

    team = relationship("Team", back_populates="owner")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    avatar_url = Column(String, index=True)

    owner = relationship("User", back_populates="team")
