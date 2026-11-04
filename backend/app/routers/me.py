"""GET, PATCH and DELETE /me, and POST /devices."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..deps import current_user, get_db, rate_limit
from ..models import Alert, Aoi, AuthCode, Delivery, Device, User
from ..schemas import DeviceIn, UserOut, UserPatchIn
from ..serializers import user_out

router = APIRouter(tags=["me"], dependencies=[Depends(rate_limit)])


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(current_user)) -> UserOut:
    return user_out(user)


@router.patch("/me", response_model=UserOut)
def patch_me(body: UserPatchIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> UserOut:
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is None and key != "name":
            continue
        setattr(user, key, value)
    db.add(user)
    db.commit()
    return user_out(user)


@router.delete("/me", status_code=204)
def delete_me(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    """Deletes the user and every row tied to them. Sessions die with the user (tokens are
    checked against the users table)."""
    alert_ids = select(Alert.id).where(Alert.user_id == user.id)
    db.execute(delete(Delivery).where(Delivery.alert_id.in_(alert_ids)))
    db.execute(delete(Alert).where(Alert.user_id == user.id))
    db.execute(delete(Aoi).where(Aoi.user_id == user.id))
    db.execute(delete(Device).where(Device.user_id == user.id))
    db.execute(delete(AuthCode).where((AuthCode.email == user.email) | (AuthCode.requester_id == user.id)))
    db.execute(delete(User).where(User.id == user.id))
    db.commit()
    return Response(status_code=204)


@router.post("/devices", status_code=204)
def register_device(body: DeviceIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    """Idempotent. A token moves to the latest user that registers it."""
    device = db.scalar(select(Device).where(Device.expo_push_token == body.expo_push_token))
    if device is None:
        db.add(Device(user_id=user.id, expo_push_token=body.expo_push_token))
    elif device.user_id != user.id:
        device.user_id = user.id
    db.commit()
    return Response(status_code=204)
