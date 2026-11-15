from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from app.core.config import COOKIE_NAME
from app.core.database import get_db
from app.core.models import User
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    email = decode_access_token(token)
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def _set_cookie(response: Response, token: str):
    # In production (HTTPS), cookies need secure=True and samesite="none" for cross-site requests
    # The frontend (vercel.app) and backend (render.com) are on different domains
    import os
    is_production = os.getenv("RENDER") == "true" or os.getenv("VERCEL") == "1"
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_production,
        samesite="none" if is_production else "lax",
        max_age=60 * 60,
        path="/",
    )

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(email=payload.email.lower(), full_name=payload.full_name, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.email)
    _set_cookie(response, token)
    return AuthResponse(user=UserResponse(id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active))

@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    token = create_access_token(user.email)
    _set_cookie(response, token)
    return AuthResponse(user=UserResponse(id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active))

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"status": "logged_out"}

@router.get("/me")
def me(request: Request, response: Response, db: Session = Depends(get_db)):
    # Ensure CORS headers are set for this endpoint
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return {"authenticated": False}
    try:
        email = decode_access_token(token)
        user = db.query(User).filter(User.email == email).first()
        if not user or not user.is_active:
            return {"authenticated": False}
        return {"authenticated": True, "user": UserResponse(id=user.id, email=user.email, full_name=user.full_name, is_active=user.is_active)}
    except Exception:
        return {"authenticated": False}