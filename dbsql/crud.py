import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
import pytz

from . import models, schemas


def get_user(db: Session, user_hash: str) -> models.User:
    return db.query(models.User).filter(models.User.user_hash == user_hash).first()


def get_user_by_osu_id(db: Session, osu_id: int) -> models.User:
    return db.query(models.User).filter(models.User.osu_id == osu_id).first()


def get_user_by_osu_username(db: Session, osu_username: str) -> models.User:
    return db.query(models.User).filter(models.User.osu_username == osu_username).first()


def get_user_by_discord_id(db: Session, discord_id: str) -> models.User:
    return db.query(models.User).filter(models.User.discord_id == discord_id).first()


def get_users(db: Session) -> List[models.User]:
    return db.query(models.User).order_by(func.lower(models.User.osu_username)).all()


def get_user_invites(db: Session, user_hash: str) -> List[models.Invite]:
    return db.query(models.Invite).filter(models.Invite.invited_user_hash == user_hash).all()


def get_team_invites(db: Session, team_hash: str) -> List[models.Invite]:
    return db.query(models.Invite).filter(models.Invite.team_hash == team_hash).all()


def get_lobbies(db: Session) -> List[models.QualifierLobby]:
    return db.query(models.QualifierLobby).order_by(models.QualifierLobby.date).all()


def get_lobby_player_count(db: Session, lobby_id: int):
    return db.query(models.Team).filter(models.Team.lobby_id == lobby_id).count()


def get_teams(db: Session, skip: int = 0, limit: int = 100) -> List[models.Team]:
    return db.query(models.Team).offset(skip).limit(limit).all()


def get_team(db: Session, team_hash: str) -> models.Team:
    return db.query(models.Team).filter(models.Team.team_hash == team_hash).first()


def count_teams(db: Session) -> int:
    return db.query(models.Team).count()


def get_invite(db: Session, team_hash: str, user_hash: str) -> models.Invite:
    return db.query(models.Invite).filter(
        models.Invite.team_hash == team_hash, models.Invite.invited_user_hash == user_hash).first()


def get_lobby(db: Session, lobby_id: int) -> models.QualifierLobby:
    return db.query(models.QualifierLobby).filter(models.QualifierLobby.id == lobby_id).first()


def create_osu_user(db: Session, user: schemas.OsuUserCreate) -> models.User:
    db_user = models.User(**user.dict(), osu_linked=True)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def leave_team(db: Session, user_hash: str) -> models.User:
    db_user = get_user(db=db, user_hash=user_hash)
    if not db_user.team:
        raise HTTPException(400, "User is not in a team")

    db_team = get_team(db=db, team_hash=db_user.team_hash)
    if len(db_team.players) == 1:
        db_team_invites = get_team_invites(db=db, team_hash=db_team.team_hash)

        for invite in db_team_invites:
            db.delete(invite)

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


def downgrade_from_discord_user(db: Session, user_hash: str) -> models.User:
    db_user = get_user(db=db, user_hash=user_hash)

    db_user.discord_id = None
    db_user.discord_tag = None
    db_user.discord_avatar_url = None
    db_user.discord_linked = False
    db.commit()
    db.refresh(db_user)
    return db_user


def create_team(db: Session, team: schemas.TeamCreate, user_hash: str, team_hash: str) -> Optional[models.Team]:
    db_user = get_user(db=db, user_hash=user_hash)
    if db_user.team_hash:
        raise HTTPException(400, "User is already on a team.")
    db_user_invites = get_user_invites(db=db, user_hash=user_hash)
    db_team = models.Team(**team.dict(), team_hash=team_hash)
    for db_invite in db_user_invites:
        db.delete(db_invite)
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    db_user.team_hash = db_team.team_hash
    db.commit()
    return db_team


def add_player_to_team(db: Session, team_hash: str, user_hash: str):
    db_invite = get_invite(db=db, team_hash=team_hash, user_hash=user_hash)
    if not db_invite:
        raise HTTPException(400, "This invite is for someone else.")

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
    if not team_owner.team_hash:
        raise HTTPException(400, "You do not have a team yet.")
    team = get_team(db=db, team_hash=team_owner.team_hash)
    invited_user = get_user_by_osu_id(db=db, osu_id=invited_user_osu_id)
    db_invite = get_invite(db=db, team_hash=team.team_hash, user_hash=invited_user.user_hash)

    if db_invite:
        raise HTTPException(400, "User is already invited.")
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


def create_avatar(db: Session, user_hash: str, img_url: str):
    db_user = get_user(db=db, user_hash=user_hash)
    if not db_user.team_hash:
        raise HTTPException(400, "User does not belong to a team.")

    db_team = get_team(db=db, team_hash=db_user.team_hash)
    db_team.avatar_url = img_url
    db.commit()
    db.refresh(db_team)
    return db_team


def add_team_to_lobby(db: Session, user_hash: str, lobby_id: int):
    lobby_teams = get_lobby_player_count(db=db, lobby_id=lobby_id)
    if lobby_teams == 6:
        raise HTTPException(401, "Lobby is full!")

    db_lobby = get_lobby(db=db, lobby_id=lobby_id)

    time_now = datetime.datetime.utcnow()
    time_now_utc = pytz.utc.localize(time_now)
    timezone = pytz.timezone("Asia/Singapore")
    time_now_in_singapore = timezone.normalize(time_now_utc)
    lobby_date = timezone.localize(db_lobby.date)
    lobby_expire = lobby_date - datetime.timedelta(minutes=30)

    if lobby_expire < time_now_in_singapore:
        raise HTTPException(401, "Lobby is closed.")

    db_user = get_user(db=db, user_hash=user_hash)
    db_team = get_team(db=db, team_hash=db_user.team_hash)
    if db_team is None:
        raise HTTPException(401, "You are not in a team.")
    if len(db_team.players) < 2:
        raise HTTPException(401, "Your team is incomplete.")
    db_team.lobby_id = lobby_id
    db.commit()
    db.refresh(db_team)
    return db_team


def remove_team_from_lobby(db: Session, user_hash: str):
    db_user = get_user(db=db, user_hash=user_hash)
    db_team = get_team(db=db, team_hash=db_user.team_hash)
    db_team.lobby_id = None
    db.commit()
    db.refresh(db_team)
    return db_team


def decline_invite(db: Session, user_hash: str, team_hash: str):
    db_invite = get_invite(db=db, user_hash=user_hash, team_hash=team_hash)
    if not db_invite:
        raise HTTPException(400, "You do not have an invite to decline.")
    db.delete(db_invite)
    db.commit()
    return get_user(db=db, user_hash=user_hash)


def cancel_invite(db: Session, user_hash: str, invited_user_osu_id: int):
    inviter_user = get_user(db=db, user_hash=user_hash)
    invited_user = get_user_by_osu_id(db=db, osu_id=invited_user_osu_id)
    db_invite = get_invite(db=db, team_hash=inviter_user.team_hash, user_hash=invited_user.user_hash)
    if not db_invite:
        raise HTTPException(400, "Invite not found.")

    db.delete(db_invite)
    db.commit()
    team_invites = get_team_invites(db=db, team_hash=inviter_user.team_hash)
    return team_invites


def ban_user(db: Session, user_osu_id: int):
    user_to_be_banned = get_user_by_osu_id(db=db, osu_id=user_osu_id)
    if user_to_be_banned.team_hash:
        team = get_team(db=db, team_hash=user_to_be_banned.team_hash)
        invites = get_team_invites(db=db, team_hash=user_to_be_banned.team_hash)
        for invite in invites:
            db.delete(invite)
        db.delete(team)
    user_to_be_banned.is_banned = True
    db.commit()
    return user_to_be_banned


def unban_user(db: Session, user_osu_id: int):
    user_to_be_unbanned = get_user_by_osu_id(db=db, osu_id=user_osu_id)
    user_to_be_unbanned.is_banned = False
    db.commit()
    return user_to_be_unbanned


def create_lobby(db: Session, lobby_name: str, lobby_time: datetime.datetime, referee_osu_username: Optional[str] = None):
    db_lobby = models.QualifierLobby(lobby_name=lobby_name, date=lobby_time,
                                     referee=referee_osu_username)
    db.add(db_lobby)
    db.commit()
    db.refresh(db_lobby)

    return db_lobby


def add_referee_to_lobby(db: Session, lobby_id: int, referee_osu_username: str):
    db_lobby = get_lobby(db=db, lobby_id=lobby_id)
    db_lobby.referee = referee_osu_username
    db.commit()
    db.refresh(db_lobby)

    return db_lobby


def remove_lobby(db: Session, lobby_id: int):
    db_lobby = get_lobby(db=db, lobby_id=lobby_id)
    if db_lobby is None:
        raise HTTPException(401, "Selected lobby does not exist.")

    db.delete(db_lobby)
    db.commit()
    return