from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.db.database import SessionLocal
from app.db.models import User
from app.schemas.user import (
    AuthTokenResponse,
    MessageResponse,
    UserCreate,
    UserLogin,
)
from app.core.security import (
    create_access_token,
    ensure_bcrypt_compatible_password,
    hash_password,
    verify_password,
)

router = APIRouter()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

        return {"access_token": token, "token_type": "bearer"}
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
