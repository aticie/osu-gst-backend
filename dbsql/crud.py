from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import models, schemas


def get_user(db: Session, user_hash: str) -> models.User:
    return db.query(models.User).filter(models.User.user_hash == user_hash).first()


def get_user_by_osu_id(db: Session, osu_id: int) -> models.User:
    return db.query(models.User).filter(models.User.osu_id == osu_id).first()


def get_user_by_discord_id(db: Session, discord_id: str) -> models.User:
    return db.query(models.User).filter(models.User.discord_id == discord_id).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()


def get_user_invites(db: Session, user_hash: str) -> List[models.Invite]:
    return db.query(models.Invite).filter(models.Invite.invited_user_hash == user_hash).all()


def get_team_invites(db: Session, team_hash: str) -> List[models.Invite]:
    return db.query(models.Invite).filter(models.Invite.team_hash == team_hash).all()


def create_osu_user(db: Session, user: schemas.OsuUserCreate) -> models.User:
    db_user = models.User(**user.dict(), osu_linked=True)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def leave_team(db: Session, user_hash: str) -> models.User:
    db_user = get_user(db=db, user_hash=user_hash)
    if db_user.team is None:
        raise HTTPException(400, "User is not in a team")

    db_team = get_team(db=db, team_hash=db_user.team_hash)
    if len(db_team.players) == 1:
        db.delete(db_team)
    else:
        db_user.team_hash = None

    db.commit()
    db.refresh(db_user)
    return db_user



def upgrade_to_discord_user(db: Session, user_hash: str, user: schemas.DiscordUser) -> models.User:
    db_user = get_user(db=db, user_hash=user_hash)

    db_user.discord_id = user.discord_id
    db_user.discord_tag = user.discord_tag
    db_user.discord_avatar_url = user.discord_avatar_url
    db_user.discord_linked = True
    db.commit()
    db.refresh(db_user)
    return db_user


def get_teams(db: Session, skip: int = 0, limit: int = 100) -> List[models.Team]:
    return db.query(models.Team).offset(skip).limit(limit).all()


def get_team(db: Session, team_hash: str) -> models.Team:
    return db.query(models.Team).filter(models.Team.team_hash == team_hash).first()


def count_teams(db: Session) -> int:
    return db.query(models.Team).count()


def get_invite(db: Session, team_hash: str, user_hash: str) -> models.Invite:
    return db.query(models.Invite).filter(
        models.Invite.team_hash == team_hash and models.Invite.invited_user_hash == user_hash).first()


def create_team(db: Session, team: schemas.TeamCreate, user_hash: str, team_hash: str) -> Optional[models.Team]:
    db_user = get_user(db=db, user_hash=user_hash)
    if db_user.team_hash:
        raise HTTPException(400, "User is already on a team.")

    db_team = models.Team(**team.dict(), team_hash=team_hash)
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    db_user.team_hash = db_team.team_hash
    db.commit()
    return db_team


def add_to_team(db: Session, team_hash: str, user_hash: str):
    db_invite = get_invite(db=db, team_hash=team_hash, user_hash=user_hash)
    if not db_invite:
        raise HTTPException(400, "Team invite for the user does not exist")

    db_user = get_user(db=db, user_hash=user_hash)
    db_team = get_team(db=db, team_hash=team_hash)
    db_user.team_hash = db_team.team_hash

    # Delete all the team invites if someone joins the team
    db.query(models.Invite).filter(models.Invite.team_hash == team_hash).delete()
    db.commit()
    db.refresh(db_user)
    return db_user


def create_invite(db: Session, invited_user_osu_id: int, team_owner_hash: str):
    team_owner = get_user(db=db, user_hash=team_owner_hash)
    team = get_team(db=db, team_hash=team_owner.team_hash)
    invited_user = get_user_by_osu_id(db=db, osu_id=invited_user_osu_id)

    if not invited_user:
        raise HTTPException(400, "Invited user has not signed-up yet.")
    if invited_user.user_hash == team_owner_hash:
        raise HTTPException(400, "The team owner does not match the current user.")
    if len(team.players) > 1:
        raise HTTPException(400, "The team is already full.")

    db_invite = models.Invite(team_hash=team_owner.team_hash, invited_user_hash=invited_user.user_hash,
                              inviter_user_hash=team_owner.user_hash)
    db.add(db_invite)
    db.commit()
    db.refresh(db_invite)
    return db_invite
