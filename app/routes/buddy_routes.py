from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.db.models import BuddyConnection, BuddyProfile, User, UserProfile
from app.routes.auth_routes import get_current_user, get_db
from app.schemas.buddy import (
    BuddyConnectionItem,
    BuddyConnectionResponse,
    BuddyPoolItem,
    BuddyStatusResponse,
    BuddyStatusUpdate,
)

router = APIRouter()


def _name_for_user(db: Session, user_id: int, fallback_email: str) -> str:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile and profile.full_name and profile.full_name.strip():
        return profile.full_name.strip()
    return fallback_email.split("@")[0]


@router.get("/me", response_model=BuddyStatusResponse)
def get_my_buddy_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(BuddyProfile).filter(BuddyProfile.user_id == current_user.id).first()
    if not profile:
        return BuddyStatusResponse(is_active=False, note=None)
    return BuddyStatusResponse(
        is_active=profile.is_active,
        note=profile.note,
    )


@router.put("/me", response_model=BuddyStatusResponse)
def update_my_buddy_status(
    payload: BuddyStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(BuddyProfile).filter(BuddyProfile.user_id == current_user.id).first()
    if not profile:
        profile = BuddyProfile(user_id=current_user.id)
        db.add(profile)

    profile.is_active = payload.is_active
    profile.mode = "buddy"
    profile.note = (payload.note or "").strip() or None
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)

    return BuddyStatusResponse(
        is_active=profile.is_active,
        note=profile.note,
    )


@router.get("/pool", response_model=list[BuddyPoolItem])
def get_buddy_pool(
    q: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profiles = (
        db.query(BuddyProfile)
        .filter(
            BuddyProfile.is_active == True,
            BuddyProfile.user_id != current_user.id,
        )
        .order_by(BuddyProfile.updated_at.desc())
        .all()
    )

    items: list[BuddyPoolItem] = []
    term = (q or "").strip().lower()
    for profile in profiles:
        user = db.query(User).filter(User.id == profile.user_id).first()
        if not user:
            continue
        name = _name_for_user(db, user.id, user.email)
        note = profile.note or ""
        if term and term not in name.lower() and term not in note.lower():
            continue
        connected = (
            db.query(BuddyConnection.id)
            .filter(
                or_(
                    and_(
                        BuddyConnection.requester_id == current_user.id,
                        BuddyConnection.target_user_id == profile.user_id,
                    ),
                    and_(
                        BuddyConnection.requester_id == profile.user_id,
                        BuddyConnection.target_user_id == current_user.id,
                    ),
                )
            )
            .first()
            is not None
        )
        items.append(
            BuddyPoolItem(
                user_id=profile.user_id,
                name=name,
                note=note,
                connected=connected,
            )
        )
    return items


@router.post("/{buddy_user_id}/connect", response_model=BuddyConnectionResponse)
def connect_with_buddy(
    buddy_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if buddy_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot connect to yourself")

    buddy = db.query(User).filter(User.id == buddy_user_id).first()
    if not buddy:
        raise HTTPException(status_code=404, detail="Buddy not found")

    buddy_profile = db.query(BuddyProfile).filter(BuddyProfile.user_id == buddy_user_id).first()
    if not buddy_profile or not buddy_profile.is_active:
        raise HTTPException(status_code=400, detail="This buddy is not currently active")

    existing = (
        db.query(BuddyConnection)
        .filter(
            or_(
                and_(
                    BuddyConnection.requester_id == current_user.id,
                    BuddyConnection.target_user_id == buddy_user_id,
                ),
                and_(
                    BuddyConnection.requester_id == buddy_user_id,
                    BuddyConnection.target_user_id == current_user.id,
                ),
            )
        )
        .first()
    )
    if existing:
        return BuddyConnectionResponse(connected=True)

    db.add(
        BuddyConnection(
            requester_id=current_user.id,
            target_user_id=buddy_user_id,
            mode="buddy",
        )
    )
    db.commit()
    return BuddyConnectionResponse(connected=True)


@router.get("/connections/me", response_model=list[BuddyConnectionItem])
def get_my_buddy_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    connections = (
        db.query(BuddyConnection)
        .filter(
            or_(
                BuddyConnection.requester_id == current_user.id,
                BuddyConnection.target_user_id == current_user.id,
            )
        )
        .order_by(BuddyConnection.created_at.desc(), BuddyConnection.id.desc())
        .all()
    )

    items: list[BuddyConnectionItem] = []
    for connection in connections:
        peer_id = (
            connection.target_user_id
            if connection.requester_id == current_user.id
            else connection.requester_id
        )
        peer = db.query(User).filter(User.id == peer_id).first()
        if not peer:
            continue
        peer_profile = db.query(BuddyProfile).filter(BuddyProfile.user_id == peer_id).first()
        note = (peer_profile.note if peer_profile else "") or ""

        items.append(
            BuddyConnectionItem(
                peer_user_id=peer_id,
                peer_name=_name_for_user(db, peer_id, peer.email),
                note=note,
                source="Buddy connection",
                created_at=connection.created_at or datetime.utcnow(),
            )
        )

    return items
