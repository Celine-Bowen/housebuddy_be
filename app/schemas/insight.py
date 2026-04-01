from datetime import datetime

from pydantic import BaseModel, Field


class AreaInsightCreate(BaseModel):
    location: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    rating_security: int = Field(ge=1, le=5)
    rating_water: int = Field(ge=1, le=5)
    rating_electricity: int = Field(ge=1, le=5)
    rating_noise: int = Field(ge=1, le=5)
    rating_traffic: int = Field(ge=1, le=5)
    note: str | None = None


class AreaInsightResponse(BaseModel):
    id: int
    user_id: int
    location: str
    latitude: float
    longitude: float
    rating_security: int
    rating_water: int
    rating_electricity: int
    rating_noise: int
    rating_traffic: int
    note: str | None
    created_at: datetime


class InsightHeatmapPointResponse(BaseModel):
    id: int
    latitude: float
    longitude: float
    location: str
    security: int
    water: int
    electricity: int
    noise: int
    traffic: int
    created_at: datetime
