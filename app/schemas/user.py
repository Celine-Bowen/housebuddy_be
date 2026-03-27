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

class UserResponse(BaseModel):
    id: int
    email: EmailStr

    class Config:
        orm_mode = True
