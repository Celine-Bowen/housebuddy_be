from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    listings = relationship(
        "Listing",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    favorites = relationship(
        "ListingFavorite",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    comments = relationship(
        "ListingComment",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    reports = relationship(
        "ListingReport",
        back_populates="reporter",
        cascade="all, delete-orphan",
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    preferred_area = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)

    user = relationship("User", back_populates="profile")


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category = Column(String, nullable=False)  # house | roommate
    title = Column(String, nullable=False)
    location = Column(String, nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    house_type = Column(String, nullable=True)
    roommate_preference = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    status = Column(String, nullable=False, default="open")  # open | taken
    rating_security = Column(Integer, nullable=False, default=3)
    rating_water = Column(Integer, nullable=False, default=3)
    rating_electricity = Column(Integer, nullable=False, default=3)
    rating_noise = Column(Integer, nullable=False, default=3)
    rating_traffic = Column(Integer, nullable=False, default=3)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="listings")
    media = relationship(
        "ListingMedia",
        back_populates="listing",
        cascade="all, delete-orphan",
        order_by="ListingMedia.id",
    )
    favorites = relationship(
        "ListingFavorite",
        back_populates="listing",
        cascade="all, delete-orphan",
    )
    comments = relationship(
        "ListingComment",
        back_populates="listing",
        cascade="all, delete-orphan",
        order_by="ListingComment.created_at",
    )
    reports = relationship(
        "ListingReport",
        back_populates="listing",
        cascade="all, delete-orphan",
    )
    connections = relationship(
        "ListingConnection",
        back_populates="listing",
        cascade="all, delete-orphan",
    )


class ListingMedia(Base):
    __tablename__ = "listing_media"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False, index=True)
    kind = Column(String, nullable=False)  # image | video
    url = Column(String, nullable=False)

    listing = relationship("Listing", back_populates="media")


class ListingFavorite(Base):
    __tablename__ = "listing_favorites"
    __table_args__ = (UniqueConstraint("listing_id", "user_id", name="uq_listing_favorite"),)

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    listing = relationship("Listing", back_populates="favorites")
    user = relationship("User", back_populates="favorites")


class ListingComment(Base):
    __tablename__ = "listing_comments"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    listing = relationship("Listing", back_populates="comments")
    user = relationship("User", back_populates="comments")


class ListingReport(Base):
    __tablename__ = "listing_reports"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reasons = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    agency_fee_flag = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    listing = relationship("Listing", back_populates="reports")
    reporter = relationship("User", back_populates="reports")


class ListingConnection(Base):
    __tablename__ = "listing_connections"
    __table_args__ = (UniqueConstraint("listing_id", "requester_id", name="uq_listing_connection"),)

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="connected")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    listing = relationship("Listing", back_populates="connections")
