from sqlalchemy.orm import Session

from . import models, schemas


def get_user(db: Session, user_hash: str):
    return db.query(models.User).filter(models.User.user_hash == user_hash).first()


def get_user_by_osu_id(db: Session, osu_id: int):
    return db.query(models.User).filter(models.User.osu_id == osu_id).first()


def get_user_by_discord_id(db: Session, discord_id: str):
    return db.query(models.User).filter(models.User.discord_id == discord_id).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_osu_user(db: Session, user: schemas.OsuUserCreate):
    db_user = models.User(**user.dict(), osu_linked=True)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def upgrade_to_discord_user(db: Session, user_hash: str, user: schemas.DiscordUser):
    db_user = get_user(db=db, user_hash=user_hash)

    db_user.discord_id = user.discord_id
    db_user.discord_tag = user.discord_tag
    db_user.discord_avatar_url = user.discord_avatar_url
    db_user.discord_linked = True
    db.commit()
    db.refresh(db_user)
    return db_user


def get_teams(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Team).offset(skip).limit(limit).all()


def get_team(db: Session, team_hash: str):
    return db.query(models.Team).filter(models.Team.team_hash == team_hash).first()


def get_invite(db: Session, team_hash: str, user_hash: str):
    return db.query(models.Invite).filter(
        models.Invite.team_hash == team_hash and models.Invite.user_hash == user_hash).first()


def create_team(db: Session, team: schemas.TeamCreate, user_hash: str):
    db_user = get_user(db=db, user_hash=user_hash)
    if db_user.team_id:
        raise Exception("User is already in a team.")
    db_team = models.Team(**team.dict())
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    db_user.team_hash = db_team.team_hash
    db.commit()
    return db_team


def add_to_team(db: Session, team_hash: str, user_hash: str):
    db_user = get_user(db=db, user_hash=user_hash)
    db_team = get_team(db=db, team_hash=team_hash)
    db_invite = get_invite(db=db, team_hash=team_hash, user_hash=user_hash)
    db_user.team_hash = db_team.team_hash
    db.delete(db_invite)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_invite(db: Session, team_hash: str, user_hash: str):
    db_invite = models.Invite(team_hash=team_hash, user_hash=user_hash)
    db.add(db_invite)
    db.commit()
    db.refresh(db_invite)
    return db_invite