from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.db.database import SessionLocal
from app.db.models import User, UserProfile
from app.schemas.user import (
    AuthTokenResponse,
    MessageResponse,
    ProfileResponse,
    ProfileUpdate,
    UserCreate,
    UserLogin,
)
from app.core.security import (
    decode_access_token,
    create_access_token,
    ensure_bcrypt_compatible_password,
    hash_password,
    verify_password,
)

router = APIRouter()
bearer_scheme = HTTPBearer()
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    db_user = db.query(User).filter(User.email == email).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found for token")

    return db_user

@router.post("/register", response_model=MessageResponse, summary="Register a new user")
@router.post("/signup", response_model=MessageResponse, summary="Signup a new user")
def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        try:
            ensure_bcrypt_compatible_password(user.password)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="Password is too long. Please use at most 72 bytes.",
            ) from exc

        existing = db.query(User).filter(User.email == user.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        new_user = User(
            email=user.email,
            hashed_password=hash_password(user.password)
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        if user.name:
            profile = UserProfile(user_id=new_user.id, full_name=user.name)
            db.add(profile)
            db.commit()

        return {"message": "User created successfully"}
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database error during signup: {exc.__class__.__name__}",
        ) from exc

@router.post("/login", response_model=AuthTokenResponse, summary="Login user")
def login(user: UserLogin, db: Session = Depends(get_db)):
    try:
        try:
            ensure_bcrypt_compatible_password(user.password)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="Password is too long. Please use at most 72 bytes.",
            ) from exc

        db_user = db.query(User).filter(User.email == user.email).first()

        if not db_user or not verify_password(user.password, db_user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token({"sub": db_user.email})

        return {
            "access_token": token,
            "token_type": "bearer",
            "email": db_user.email,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database error during login: {exc.__class__.__name__}",
        ) from exc

@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password (basic)",
)
def reset_password(user: UserLogin, db: Session = Depends(get_db)):
    try:
        ensure_bcrypt_compatible_password(user.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Password is too long. Please use at most 72 bytes.",
        ) from exc

    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.hashed_password = hash_password(user.password)
    db.commit()

    return {"message": "Password updated"}


@router.get("/me", response_model=ProfileResponse, summary="Get own profile")
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        return {
            "email": current_user.email,
            "full_name": None,
            "phone_number": None,
            "preferred_area": None,
            "bio": None,
            "avatar_url": None,
        }

    return {
        "email": current_user.email,
        "full_name": profile.full_name,
        "phone_number": profile.phone_number,
        "preferred_area": profile.preferred_area,
        "bio": profile.bio,
        "avatar_url": profile.avatar_url,
    }


@router.put("/me", response_model=ProfileResponse, summary="Update own profile")
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    profile.full_name = payload.full_name
    profile.phone_number = payload.phone_number
    profile.preferred_area = payload.preferred_area
    profile.bio = payload.bio
    db.commit()
    db.refresh(profile)

    return {
        "email": current_user.email,
        "full_name": profile.full_name,
        "phone_number": profile.phone_number,
        "preferred_area": profile.preferred_area,
        "bio": profile.bio,
        "avatar_url": profile.avatar_url,
    }


@router.post("/me/avatar", response_model=ProfileResponse, summary="Upload own profile photo")
def upload_profile_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    extension = Path(file.filename or "").suffix.lower()
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    has_image_content_type = (file.content_type or "").startswith("image/")
    has_allowed_extension = extension in allowed_extensions
    if not has_image_content_type and not has_allowed_extension:
        raise HTTPException(
            status_code=400,
            detail="Only image uploads are allowed (.jpg, .jpeg, .png, .webp)",
        )
    if extension not in allowed_extensions:
        extension = ".jpg"

    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    filename = f"profile_{current_user.id}_{uuid4().hex}{extension}"
    destination = UPLOADS_DIR / filename
    contents = file.file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 5MB)")
    destination.write_bytes(contents)

    if profile.avatar_url:
        old_file = Path(profile.avatar_url.lstrip("/"))
        if old_file.exists() and old_file.is_file():
            old_file.unlink(missing_ok=True)

    profile.avatar_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(profile)

    return {
        "email": current_user.email,
        "full_name": profile.full_name,
        "phone_number": profile.phone_number,
        "preferred_area": profile.preferred_area,
        "bio": profile.bio,
        "avatar_url": profile.avatar_url,
    }


@router.delete("/me", response_model=MessageResponse, summary="Delete own account")
def delete_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    if profile:
        db.delete(profile)
    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted"}
