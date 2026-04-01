from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models import AreaInsight, User
from app.routes.auth_routes import get_current_user, get_db
from app.schemas.insight import (
    AreaInsightCreate,
    AreaInsightResponse,
    InsightHeatmapPointResponse,
)

router = APIRouter()


def _to_response(insight: AreaInsight) -> AreaInsightResponse:
    return AreaInsightResponse(
        id=insight.id,
        user_id=insight.user_id,
        location=insight.location,
        latitude=insight.latitude,
        longitude=insight.longitude,
        rating_security=insight.rating_security,
        rating_water=insight.rating_water,
        rating_electricity=insight.rating_electricity,
        rating_noise=insight.rating_noise,
        rating_traffic=insight.rating_traffic,
        note=insight.note,
        created_at=insight.created_at or datetime.utcnow(),
    )


@router.post("", response_model=AreaInsightResponse)
def create_area_insight(
    payload: AreaInsightCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    insight = AreaInsight(
        user_id=current_user.id,
        location=payload.location.strip(),
        latitude=payload.latitude,
        longitude=payload.longitude,
        rating_security=payload.rating_security,
        rating_water=payload.rating_water,
        rating_electricity=payload.rating_electricity,
        rating_noise=payload.rating_noise,
        rating_traffic=payload.rating_traffic,
        note=(payload.note or "").strip() or None,
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return _to_response(insight)


@router.get("/heatmap/points", response_model=list[InsightHeatmapPointResponse])
def get_insight_heatmap_points(
    location: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(AreaInsight)
    if location:
        query = query.filter(AreaInsight.location.ilike(f"%{location.strip()}%"))

    insights = (
        query.order_by(AreaInsight.created_at.desc(), AreaInsight.id.desc())
        .limit(limit)
        .all()
    )

    return [
        InsightHeatmapPointResponse(
            id=item.id,
            latitude=item.latitude,
            longitude=item.longitude,
            location=item.location,
            security=item.rating_security,
            water=item.rating_water,
            electricity=item.rating_electricity,
            noise=item.rating_noise,
            traffic=item.rating_traffic,
            created_at=item.created_at or datetime.utcnow(),
        )
        for item in insights
    ]
