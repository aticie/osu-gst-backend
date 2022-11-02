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
    db_user: models.User = db.\
        query(models.User).\
        filter(models.User.user_hash == user_hash).\
        first()

    db_user.discord_id = user.discord_id
    db_user.discord_tag = user.discord_tag
    db_user.discord_avatar_url = user.discord_avatar_url
    db_user.discord_linked = True
    db.commit()
    db.refresh(db_user)
    return db_user

def get_teams(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Team).offset(skip).limit(limit).all()


def create_user_item(db: Session, item: schemas.TeamCreate, user_id: int):
    db_item = models.Team(**item.dict(), owner_id=user_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item