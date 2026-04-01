from datetime import datetime
from pathlib import Path
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models import (
    Listing,
    ListingComment,
    ListingConnection,
    ListingFavorite,
    ListingMedia,
    ListingReport,
    User,
    UserProfile,
)
from app.routes.auth_routes import get_current_user, get_db
from app.schemas.listing import (
    HeatmapAveragesResponse,
    ListingCommentCreate,
    ListingCommentResponse,
    ListingConnectionItem,
    ListingConnectionResponse,
    ListingCreate,
    ListingMediaPayload,
    ListingMediaUploadResponse,
    ListingMutationResponse,
    ListingReportCreate,
    ListingResponse,
    ListingStatusUpdate,
    ListingUpdate,
)

router = APIRouter()
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _name_for_user(db: Session, user_id: int, fallback_email: str) -> str:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile and profile.full_name and profile.full_name.strip():
        return profile.full_name.strip()
    return fallback_email.split("@")[0]


def _to_response(db: Session, listing: Listing, current_user_id: int) -> ListingResponse:
    favorites_count = (
        db.query(func.count(ListingFavorite.id))
        .filter(ListingFavorite.listing_id == listing.id)
        .scalar()
        or 0
    )
    comments_count = (
        db.query(func.count(ListingComment.id))
        .filter(ListingComment.listing_id == listing.id)
        .scalar()
        or 0
    )
    is_favorited = (
        db.query(ListingFavorite.id)
        .filter(
            ListingFavorite.listing_id == listing.id,
            ListingFavorite.user_id == current_user_id,
        )
        .first()
        is not None
    )
    is_connected = (
        db.query(ListingConnection.id)
        .filter(
            ListingConnection.listing_id == listing.id,
            ListingConnection.requester_id == current_user_id,
            ListingConnection.status == "connected",
        )
        .first()
        is not None
    )

    poster = db.query(User).filter(User.id == listing.user_id).first()
    poster_email = poster.email if poster else "unknown@example.com"
    poster_name = _name_for_user(db, listing.user_id, poster_email)

    return ListingResponse(
        id=listing.id,
        category=listing.category,
        title=listing.title,
        location=listing.location,
        amount=listing.amount,
        description=listing.description,
        house_type=listing.house_type,
        roommate_preference=listing.roommate_preference,
        contact_phone=listing.contact_phone,
        status=listing.status,
        rating_security=listing.rating_security,
        rating_water=listing.rating_water,
        rating_electricity=listing.rating_electricity,
        rating_noise=listing.rating_noise,
        rating_traffic=listing.rating_traffic,
        created_at=listing.created_at or datetime.utcnow(),
        poster_name=poster_name,
        poster_email=poster_email,
        media=[ListingMediaPayload(kind=m.kind, url=m.url) for m in listing.media],
        favorites_count=int(favorites_count),
        comments_count=int(comments_count),
        is_favorited=is_favorited,
        is_owner=listing.user_id == current_user_id,
        is_connected=is_connected,
    )


def _validate_roommate_phone(category: str, contact_phone: str | None) -> None:
    if category == "roommate" and not (contact_phone or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Phone number is required for roommate listings",
        )


def _normalize_and_validate_phone(contact_phone: str | None) -> str | None:
    value = (contact_phone or "").strip()
    if not value:
        return None
    compact = re.sub(r"[\s\-]", "", value)
    if compact.startswith("+"):
        compact = compact[1:]

    is_local = compact.startswith("0") and len(compact) == 10 and compact.isdigit()
    is_intl = compact.startswith("254") and len(compact) == 12 and compact.isdigit()
    if not (is_local or is_intl):
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number. Use format 07XXXXXXXX or 2547XXXXXXX",
        )
    return compact


@router.post("/media", response_model=ListingMediaUploadResponse)
def upload_listing_media(
    files: list[UploadFile] = File(...),
    _: User = Depends(get_current_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    result: list[ListingMediaPayload] = []
    allowed_images = {".jpg", ".jpeg", ".png", ".webp"}
    allowed_videos = {".mp4", ".mov", ".webm", ".m4v"}

    for file in files:
        extension = Path(file.filename or "").suffix.lower()
        content_type = (file.content_type or "").lower()
        is_image = content_type.startswith("image/") or extension in allowed_images
        is_video = content_type.startswith("video/") or extension in allowed_videos

        if not is_image and not is_video:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Use image/video formats only.",
            )

        if extension == "":
            extension = ".jpg" if is_image else ".mp4"

        file.file.seek(0)
        contents = file.file.read()
        if not contents:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty. Please reselect and upload again.",
            )
        max_size = 5 * 1024 * 1024 if is_image else 25 * 1024 * 1024
        if len(contents) > max_size:
            kind_name = "Image" if is_image else "Video"
            raise HTTPException(
                status_code=400,
                detail=f"{kind_name} too large. Max size is {max_size // (1024 * 1024)}MB",
            )

        filename = f"listing_{uuid4().hex}{extension}"
        destination = UPLOADS_DIR / filename
        destination.write_bytes(contents)

        result.append(
            ListingMediaPayload(
                kind="image" if is_image else "video",
                url=f"/uploads/{filename}",
            )
        )

    return ListingMediaUploadResponse(media=result)


@router.post("", response_model=ListingResponse)
def create_listing(
    payload: ListingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.media:
        raise HTTPException(
            status_code=400,
            detail="At least one image or video is required",
        )
    normalized_phone = _normalize_and_validate_phone(payload.contact_phone)
    _validate_roommate_phone(payload.category, normalized_phone)
    listing = Listing(
        user_id=current_user.id,
        category=payload.category,
        title=payload.title.strip(),
        location=payload.location.strip(),
        amount=payload.amount,
        description=(payload.description or "").strip() or None,
        house_type=(payload.house_type or "").strip() or None,
        roommate_preference=(payload.roommate_preference or "").strip() or None,
        contact_phone=normalized_phone,
        status="open",
        rating_security=payload.rating_security,
        rating_water=payload.rating_water,
        rating_electricity=payload.rating_electricity,
        rating_noise=payload.rating_noise,
        rating_traffic=payload.rating_traffic,
    )
    db.add(listing)
    db.flush()

    for item in payload.media:
        db.add(
            ListingMedia(
                listing_id=listing.id,
                kind=item.kind,
                url=item.url,
            )
        )

    db.commit()
    db.refresh(listing)
    return _to_response(db, listing, current_user.id)


@router.put("/{listing_id}", response_model=ListingResponse)
def update_listing(
    listing_id: int,
    payload: ListingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only poster can edit listing")

    if payload.title is not None:
        listing.title = payload.title.strip()
    if payload.location is not None:
        listing.location = payload.location.strip()
    if payload.amount is not None:
        listing.amount = payload.amount

    if payload.description is not None:
        listing.description = payload.description.strip() or None
    if payload.house_type is not None:
        listing.house_type = payload.house_type.strip() or None
    if payload.roommate_preference is not None:
        listing.roommate_preference = payload.roommate_preference.strip() or None
    if payload.contact_phone is not None:
        listing.contact_phone = _normalize_and_validate_phone(payload.contact_phone)

    if payload.rating_security is not None:
        listing.rating_security = payload.rating_security
    if payload.rating_water is not None:
        listing.rating_water = payload.rating_water
    if payload.rating_electricity is not None:
        listing.rating_electricity = payload.rating_electricity
    if payload.rating_noise is not None:
        listing.rating_noise = payload.rating_noise
    if payload.rating_traffic is not None:
        listing.rating_traffic = payload.rating_traffic

    _validate_roommate_phone(listing.category, listing.contact_phone)

    if payload.media is not None:
        if not payload.media:
            raise HTTPException(
                status_code=400,
                detail="At least one image or video is required",
            )
        db.query(ListingMedia).filter(ListingMedia.listing_id == listing.id).delete()
        for item in payload.media:
            db.add(
                ListingMedia(
                    listing_id=listing.id,
                    kind=item.kind,
                    url=item.url,
                )
            )

    db.commit()
    db.refresh(listing)
    return _to_response(db, listing, current_user.id)


@router.get("", response_model=list[ListingResponse])
def get_listings(
    category: str | None = Query(default=None, pattern="^(house|roommate)$"),
    status: str | None = Query(default=None, pattern="^(open|taken)$"),
    location: str | None = None,
    min_amount: int | None = Query(default=None, ge=0),
    max_amount: int | None = Query(default=None, ge=0),
    favorites_only: bool = False,
    mine_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Listing)

    if category:
        query = query.filter(Listing.category == category)
    if status:
        query = query.filter(Listing.status == status)
    if location:
        query = query.filter(Listing.location.ilike(f"%{location.strip()}%"))
    if min_amount is not None:
        query = query.filter(Listing.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Listing.amount <= max_amount)
    if mine_only:
        query = query.filter(Listing.user_id == current_user.id)
    if favorites_only:
        query = query.join(
            ListingFavorite,
            (ListingFavorite.listing_id == Listing.id)
            & (ListingFavorite.user_id == current_user.id),
        )

    listings = query.order_by(Listing.created_at.desc(), Listing.id.desc()).all()
    return [_to_response(db, item, current_user.id) for item in listings]


@router.get("/heatmap/averages", response_model=HeatmapAveragesResponse)
def get_heatmap_averages(
    location: str | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Listing).filter(Listing.status == "open")
    if location:
        query = query.filter(Listing.location.ilike(f"%{location.strip()}%"))
    listings = query.all()
    if not listings:
        return HeatmapAveragesResponse(
            security=0,
            water=0,
            electricity=0,
            noise=0,
            traffic=0,
            listings_count=0,
        )

    total = len(listings)
    return HeatmapAveragesResponse(
        security=round(sum(item.rating_security for item in listings) / total, 2),
        water=round(sum(item.rating_water for item in listings) / total, 2),
        electricity=round(sum(item.rating_electricity for item in listings) / total, 2),
        noise=round(sum(item.rating_noise for item in listings) / total, 2),
        traffic=round(sum(item.rating_traffic for item in listings) / total, 2),
        listings_count=total,
    )


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _to_response(db, listing, current_user.id)


@router.patch("/{listing_id}/status", response_model=ListingResponse)
def update_listing_status(
    listing_id: int,
    payload: ListingStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only poster can update status")

    listing.status = payload.status
    db.commit()
    db.refresh(listing)
    return _to_response(db, listing, current_user.id)


@router.post("/{listing_id}/favorite", response_model=ListingMutationResponse)
def save_listing(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    existing = (
        db.query(ListingFavorite)
        .filter(
            ListingFavorite.listing_id == listing_id,
            ListingFavorite.user_id == current_user.id,
        )
        .first()
    )
    if not existing:
        db.add(ListingFavorite(listing_id=listing_id, user_id=current_user.id))
        db.commit()

    return ListingMutationResponse(message="Listing saved")


@router.delete("/{listing_id}/favorite", response_model=ListingMutationResponse)
def unsave_listing(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    favorite = (
        db.query(ListingFavorite)
        .filter(
            ListingFavorite.listing_id == listing_id,
            ListingFavorite.user_id == current_user.id,
        )
        .first()
    )
    if favorite:
        db.delete(favorite)
        db.commit()
    return ListingMutationResponse(message="Listing removed from favorites")


@router.get("/{listing_id}/comments", response_model=list[ListingCommentResponse])
def get_listing_comments(
    listing_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    comments = (
        db.query(ListingComment)
        .filter(ListingComment.listing_id == listing_id)
        .order_by(ListingComment.created_at.asc(), ListingComment.id.asc())
        .all()
    )

    response: list[ListingCommentResponse] = []
    for comment in comments:
        user = db.query(User).filter(User.id == comment.user_id).first()
        email = user.email if user else "unknown@example.com"
        response.append(
            ListingCommentResponse(
                id=comment.id,
                user_name=_name_for_user(db, comment.user_id, email),
                body=comment.body,
                created_at=comment.created_at or datetime.utcnow(),
            )
        )
    return response


@router.post("/{listing_id}/comments", response_model=ListingMutationResponse)
def add_listing_comment(
    listing_id: int,
    payload: ListingCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    text = payload.body.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Comment cannot be empty")

    db.add(ListingComment(listing_id=listing_id, user_id=current_user.id, body=text))
    db.commit()
    return ListingMutationResponse(message="Comment added")


@router.post("/{listing_id}/reports", response_model=ListingMutationResponse)
def report_listing(
    listing_id: int,
    payload: ListingReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    reasons_text = ", ".join([r.strip() for r in payload.reasons if r.strip()])
    details_text = (payload.details or "").strip() or None

    db.add(
        ListingReport(
            listing_id=listing_id,
            reporter_id=current_user.id,
            reasons=reasons_text or None,
            details=details_text,
            agency_fee_flag=payload.agency_fee_flag,
        )
    )
    db.commit()
    return ListingMutationResponse(message="Report submitted")


@router.get("/{listing_id}/connection", response_model=ListingConnectionResponse)
def get_connection_state(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    connected = (
        db.query(ListingConnection.id)
        .filter(
            ListingConnection.listing_id == listing_id,
            ListingConnection.requester_id == current_user.id,
            ListingConnection.status == "connected",
        )
        .first()
        is not None
    )
    return ListingConnectionResponse(connected=connected)


@router.post("/{listing_id}/connect", response_model=ListingConnectionResponse)
def connect_listing(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot connect to your own listing")

    existing = (
        db.query(ListingConnection)
        .filter(
            ListingConnection.listing_id == listing_id,
            ListingConnection.requester_id == current_user.id,
        )
        .first()
    )
    if not existing:
        db.add(
            ListingConnection(
                listing_id=listing_id,
                requester_id=current_user.id,
                owner_id=listing.user_id,
                status="connected",
            )
        )
        db.commit()

    return ListingConnectionResponse(connected=True)


@router.get("/connections/me", response_model=list[ListingConnectionItem])
def get_my_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    connections = (
        db.query(ListingConnection)
        .filter(
            or_(
                ListingConnection.requester_id == current_user.id,
                ListingConnection.owner_id == current_user.id,
            ),
            ListingConnection.status == "connected",
        )
        .order_by(ListingConnection.created_at.desc(), ListingConnection.id.desc())
        .all()
    )
    items: list[ListingConnectionItem] = []
    for connection in connections:
        listing = db.query(Listing).filter(Listing.id == connection.listing_id).first()
        if not listing:
            continue
        requester = db.query(User).filter(User.id == connection.requester_id).first()
        owner = db.query(User).filter(User.id == connection.owner_id).first()

        if connection.requester_id == current_user.id:
            peer_id = connection.owner_id
            fallback_email = owner.email if owner else "unknown@example.com"
        else:
            peer_id = connection.requester_id
            fallback_email = requester.email if requester else "unknown@example.com"

        items.append(
            ListingConnectionItem(
                listing_id=listing.id,
                listing_title=listing.title,
                peer_name=_name_for_user(db, peer_id, fallback_email),
                source="Listing connection",
            )
        )
    return items
