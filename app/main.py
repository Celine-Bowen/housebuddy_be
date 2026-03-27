from fastapi import FastAPI
from app.routes import user_routes, auth_routes

app = FastAPI(title="HomeBuddy Backend")

# Include routes
# app.include_router(user_routes.router, prefix="/users", tags=["users"])
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])

@app.get("/")
def root():
    return {"message": "Welcome to HomeBuddy Backend"}