from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    full_name: str | None = None
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    is_active: bool

class AuthResponse(BaseModel):
    user: UserResponse