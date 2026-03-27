import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import user_routes, auth_routes
from app.db.database import Base, engine
from app.db import models  # noqa: F401

app = FastAPI(title="HomeBuddy Backend")

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

@app.on_event("startup")
def on_startup() -> None:
    # Dev-friendly: ensure core tables exist for UI testing.
    Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "Welcome to HomeBuddy Backend"}
