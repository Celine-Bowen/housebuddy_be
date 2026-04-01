from datetime import datetime
from pydantic import BaseModel, Field


class ListingMediaPayload(BaseModel):
    kind: str = Field(pattern='^(image|video)$')
    url: str


class ListingCreate(BaseModel):
    category: str = Field(pattern='^(house|roommate)$')
    title: str
    location: str
    amount: int = Field(ge=0)
    description: str | None = None
    house_type: str | None = None
    roommate_preference: str | None = None
    contact_phone: str | None = None
    rating_security: int = Field(ge=1, le=5, default=3)
    rating_water: int = Field(ge=1, le=5, default=3)
    rating_electricity: int = Field(ge=1, le=5, default=3)
    rating_noise: int = Field(ge=1, le=5, default=3)
    rating_traffic: int = Field(ge=1, le=5, default=3)
    media: list[ListingMediaPayload] = Field(min_length=1)


class ListingUpdate(BaseModel):
    title: str | None = None
    location: str | None = None
    amount: int | None = Field(default=None, ge=0)
    description: str | None = None
    house_type: str | None = None
    roommate_preference: str | None = None
    contact_phone: str | None = None
    rating_security: int | None = Field(default=None, ge=1, le=5)
    rating_water: int | None = Field(default=None, ge=1, le=5)
    rating_electricity: int | None = Field(default=None, ge=1, le=5)
    rating_noise: int | None = Field(default=None, ge=1, le=5)
    rating_traffic: int | None = Field(default=None, ge=1, le=5)
    media: list[ListingMediaPayload] | None = None


class ListingStatusUpdate(BaseModel):
    status: str = Field(pattern='^(open|taken)$')


class ListingCommentCreate(BaseModel):
    body: str


class ListingReportCreate(BaseModel):
    reasons: list[str] = Field(default_factory=list)
    details: str | None = None
    agency_fee_flag: bool = False


class ListingCommentResponse(BaseModel):
    id: int
    user_name: str
    body: str
    created_at: datetime


class ListingResponse(BaseModel):
    id: int
    category: str
    title: str
    location: str
    amount: int
    description: str | None
    house_type: str | None
    roommate_preference: str | None
    contact_phone: str | None
    status: str
    rating_security: int
    rating_water: int
    rating_electricity: int
    rating_noise: int
    rating_traffic: int
    created_at: datetime
    poster_name: str
    poster_email: str
    media: list[ListingMediaPayload]
    favorites_count: int
    comments_count: int
    is_favorited: bool
    is_owner: bool
    is_connected: bool


class ListingMutationResponse(BaseModel):
    message: str


class ListingMediaUploadResponse(BaseModel):
    media: list[ListingMediaPayload]


class HeatmapAveragesResponse(BaseModel):
    security: float
    water: float
    electricity: float
    noise: float
    traffic: float
    listings_count: int


class ListingConnectionResponse(BaseModel):
    connected: bool


class ListingConnectionItem(BaseModel):
    listing_id: int
    listing_title: str
    peer_name: str
    source: str
