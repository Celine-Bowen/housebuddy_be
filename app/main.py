import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.routes import auth_routes, listing_routes, user_routes
from app.db.database import Base, engine
from app.db import models  # noqa: F401

app = FastAPI(title="HomeBuddy Backend")
os.makedirs("uploads", exist_ok=True)

# origins = [
#     "http://localhost:56570",  # your frontend
#     "http://127.0.0.1:56570",
# ]

# allow_origins=["*"]
origins = ["*"]

app.add_middleware(
     CORSMiddleware,
    allow_origins=origins,  # or ["*"] for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
# app.include_router(user_routes.router, prefix="/users", tags=["users"])
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(listing_routes.router, prefix="/listings", tags=["listings"])
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.on_event("startup")
def on_startup() -> None:
    # Dev-friendly: ensure core tables exist for UI testing.
    Base.metadata.create_all(bind=engine)
    # Keep local/dev DB in sync for new profile avatar field.
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE user_profiles "
                "ADD COLUMN IF NOT EXISTS avatar_url VARCHAR"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE listings "
                "ADD COLUMN IF NOT EXISTS rating_security INTEGER DEFAULT 3"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE listings "
                "ADD COLUMN IF NOT EXISTS rating_water INTEGER DEFAULT 3"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE listings "
                "ADD COLUMN IF NOT EXISTS rating_electricity INTEGER DEFAULT 3"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE listings "
                "ADD COLUMN IF NOT EXISTS rating_noise INTEGER DEFAULT 3"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE listings "
                "ADD COLUMN IF NOT EXISTS rating_traffic INTEGER DEFAULT 3"
            )
        )

@app.get("/")
def root():
    return {"message": "Welcome to HomeBuddy Backend"}
