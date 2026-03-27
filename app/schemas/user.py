from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class MessageResponse(BaseModel):
    message: str

class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str
    email: EmailStr

class ProfileUpdate(BaseModel):
    full_name: str | None = None
    phone_number: str | None = None
    preferred_area: str | None = None
    bio: str | None = None

class ProfileResponse(BaseModel):
    email: EmailStr
    full_name: str | None = None
    phone_number: str | None = None
    preferred_area: str | None = None
    bio: str | None = None
    avatar_url: str | None = None

class UserResponse(BaseModel):
    id: int
    email: EmailStr

    class Config:
        orm_mode = True
