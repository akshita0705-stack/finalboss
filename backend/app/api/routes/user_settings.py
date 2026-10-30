from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.privacy_models import UserSetting
from app.models.user import User
from app.schemas.user_settings import UserSettingsResponse, UserSettingsUpdate

router = APIRouter(prefix="/user/settings", tags=["User Settings"])


def get_or_create_settings(db: Session, user_id: str) -> UserSetting:
    """Return this user's settings row; create it with defaults on first use."""
    row = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
    if row is None:
        row = UserSetting(user_id=user_id)
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            # Two requests created it at the same time; use the one that won.
            db.rollback()
            row = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
        else:
            db.refresh(row)
    return row


@router.get("", response_model=UserSettingsResponse)
def get_my_settings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the logged-in user's own settings."""
    return get_or_create_settings(db, user.id)


@router.put("", response_model=UserSettingsResponse)
def update_my_settings(
    updates: UserSettingsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update only the fields that were sent. Other users' rows are never touched."""
    row = get_or_create_settings(db, user.id)
    data = updates.model_dump(exclude_unset=True)

    if "notification_preferences" in data and data["notification_preferences"] is not None:
        # Merge so sending one key does not erase the other.
        row.notification_preferences = {
            **(row.notification_preferences or {}),
            **data.pop("notification_preferences"),
        }
    for field, value in data.items():
        if value is not None:
            setattr(row, field, value)

    db.commit()
    db.refresh(row)
    return row


@router.post("/pause", response_model=UserSettingsResponse)
def pause_monitoring(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_or_create_settings(db, user.id)
    row.monitoring_enabled = False
    db.commit()
    db.refresh(row)
    return row


@router.post("/resume", response_model=UserSettingsResponse)
def resume_monitoring(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_or_create_settings(db, user.id)
    row.monitoring_enabled = True
    db.commit()
    db.refresh(row)
    return row